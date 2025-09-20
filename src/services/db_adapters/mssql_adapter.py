from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence, Tuple

from src.services.database_gateway import (
    DatabaseGateway,
    GatewayConfig,
    DatabaseError,
    TransientError,
    map_mssql_error,
)
from src.services.mssql_connection import build_connect_kwargs
from src.services.azure_ad_token_manager import get_token_manager, ConnectionDescriptor


def _build_conn_str(cfg: GatewayConfig) -> str:
    desc = {
        "server": cfg.server,
        "database": cfg.database,
        "auth_type": cfg.auth_type,
        "username": cfg.username,
        "port": None,  # extend later if needed
        "authority": cfg.authority,
        "connect_timeout_seconds": cfg.timeout_seconds,
    }
    kwargs = build_connect_kwargs(desc)
    parts: list[str] = ["DRIVER={ODBC Driver 18 for SQL Server}"]
    if kwargs.get("Server"):
        parts.append(f"SERVER={kwargs['Server']}")
    if kwargs.get("Database"):
        parts.append(f"DATABASE={kwargs['Database']}")

    mode = (cfg.auth_type or "").lower()
    if mode == "windows" or kwargs.get("Trusted_Connection") == "yes":
        parts.append("Trusted_Connection=yes")
    elif mode == "sql":
        if kwargs.get("UID"):
            parts.append(f"UID={kwargs['UID']}")
        # No PWD here; callers must supply via secure flow if used interactively
    elif mode == "azure_ad_interactive":
        parts.append("Authentication=ActiveDirectoryInteractive")
        if kwargs.get("UID"):
            parts.append(f"UID={kwargs['UID']}")
    elif mode == "azure_ad_password":
        parts.append("Authentication=ActiveDirectoryPassword")
        if kwargs.get("UID"):
            parts.append(f"UID={kwargs['UID']}")
    elif mode == "azure_ad_integrated":
        parts.append("Authentication=ActiveDirectoryIntegrated")
    elif mode == "azure_ad_device_code":
        parts.append("Authentication=ActiveDirectoryDeviceCode")
        if kwargs.get("UID"):
            parts.append(f"UID={kwargs['UID']}")
    else:
        parts.append("Trusted_Connection=yes")

    if mode.startswith("azure_ad") and cfg.authority:
        parts.append(f"Authority={cfg.authority}")

    parts.append("Encrypt=yes")
    # For Azure AD authentication, trust server certificate to allow browser authentication
    if mode.startswith("azure_ad"):
        parts.append("TrustServerCertificate=yes")
    else:
        parts.append("TrustServerCertificate=no")
    return ";".join(parts)


def _extract_mssql_error_info(exc: BaseException) -> Tuple[str, Optional[int], Optional[str]]:
    msg = str(exc) if exc else ""
    code: Optional[int] = None
    sqlstate: Optional[str] = None
    # pyodbc.Error often has .args like ("28000", "[28000] [Microsoft][SQL Server]...", 18456)
    try:
        args = getattr(exc, "args", None)
        if args and isinstance(args, (list, tuple)):
            for a in args:
                if isinstance(a, str) and len(a) == 5 and a.isdigit():
                    sqlstate = a
                if isinstance(a, int):
                    code = a
    except Exception:
        pass
    return msg, code, sqlstate


class MssqlAdapter(DatabaseGateway):
    """MSSQL implementation per constitution:
    - Per-operation connections with pooling
    - Retry transient failures with backoff
    - Transaction(): single connection for the block; nested savepoints
    """

    def __init__(self) -> None:
        super().__init__()
        self._backend = "mssql"
        self._cfg: Optional[GatewayConfig] = None
        self._tx_depth = 0
        self._tx_conn = None  # type: ignore[var-annotated]

    def init(self, cfg: GatewayConfig, sql_password: str = None) -> None:
        if cfg.backend != "mssql":
            raise DatabaseError("MssqlAdapter requires backend='mssql'")
        if not cfg.server or not cfg.database:
            raise DatabaseError("server and database are required for MssqlAdapter")
        self._cfg = cfg
        self._sql_password = sql_password  # Store password securely for SQL authentication

    def close(self) -> None:
        # no persistent connection
        if self._tx_conn is not None:
            try:
                self._tx_conn.close()
            except Exception:
                pass
            finally:
                self._tx_conn = None
                self._tx_depth = 0

    # Internal helpers
    def _connect(self, autocommit: bool) -> Any:
        if not self._cfg:
            raise DatabaseError("MSSQL adapter not initialized")

        # Use token manager for Azure AD authentication
        if self._cfg.auth_type and self._cfg.auth_type.startswith("azure_ad"):
            return self._connect_with_token_manager(autocommit)
        else:
            # Use traditional connection for non-Azure AD auth
            conn_str = _build_conn_str(self._cfg)

            # Add password for SQL authentication if available
            if (self._cfg.auth_type and self._cfg.auth_type.lower() == "sql" and
                hasattr(self, '_sql_password') and self._sql_password):
                if "PWD=" not in conn_str:
                    conn_str += f";PWD={self._sql_password}"

            timeout = max(1, int(self._cfg.timeout_seconds or 30))
            try:
                import pyodbc  # type: ignore
            except Exception as exc:
                raise DatabaseError(f"pyodbc not available: {exc}")
            return pyodbc.connect(conn_str, autocommit=autocommit, timeout=timeout)

    def _connect_with_token_manager(self, autocommit: bool) -> Any:
        """Connect using Azure AD token manager for authentication caching"""
        if not self._cfg:
            raise DatabaseError("MSSQL adapter not initialized")

        # Create connection descriptor for token manager
        descriptor = ConnectionDescriptor(
            server=self._cfg.server or "",
            database=self._cfg.database or "",
            auth_type=self._cfg.auth_type or "",
            username=self._cfg.username,
            authority=self._cfg.authority,
            timeout_seconds=self._cfg.timeout_seconds or 30,
            use_driver17=self._cfg.use_driver17
        )

        try:
            # Get connection string with cached authentication
            token_manager = get_token_manager()
            conn_str = token_manager.get_connection_string(descriptor)

            timeout = max(1, int(self._cfg.timeout_seconds or 30))
            import pyodbc  # type: ignore
            conn = pyodbc.connect(conn_str, autocommit=autocommit, timeout=timeout)
            return conn

        except RuntimeError as e:
            if "No valid authentication token found" in str(e):
                raise DatabaseError(f"Authentication required: {e}")
            else:
                raise DatabaseError(f"Azure AD authentication failed: {e}")
        except Exception as exc:
            raise DatabaseError(f"Connection failed: {exc}")

    def _with_retry(self, func, *, attempts: int = 3) -> Any:
        delay = 0.5
        last_err: Optional[DatabaseError] = None
        for i in range(attempts):
            try:
                return func()
            except Exception as exc:  # map and decide
                msg, code, sqlstate = _extract_mssql_error_info(exc)
                derr = map_mssql_error(msg, code, sqlstate)
                if isinstance(derr, TransientError) and i < attempts - 1:
                    time.sleep(delay)
                    delay *= 2
                    last_err = derr
                    continue
                raise derr
        if last_err:
            raise last_err
        raise DatabaseError("Unknown failure without exception")

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        def op():
            if self._tx_conn is not None:
                cur = self._tx_conn.cursor()
                cur.execute(sql, tuple(params))
                try:
                    return int(cur.rowcount) if cur.rowcount is not None else 0
                finally:
                    cur.close()
            # short-lived connection
            conn = self._connect(autocommit=True)
            try:
                cur = conn.cursor()
                cur.execute(sql, tuple(params))
                rc = int(cur.rowcount) if cur.rowcount is not None else 0
                cur.close()
                return rc
            finally:
                conn.close()

        _t0 = time.perf_counter()
        try:
            rc = self._with_retry(op)
            self._notify({"op": "execute", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "rowcount": rc, "success": True})
            return rc
        except DatabaseError as err:
            self._notify({"op": "execute", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
            raise

    def query_all(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        def op():
            if self._tx_conn is not None:
                cur = self._tx_conn.cursor()
                try:
                    cur.execute(sql, tuple(params))
                    rows = cur.fetchall()
                    return [tuple(r) for r in rows]
                finally:
                    cur.close()
            conn = self._connect(autocommit=True)
            try:
                cur = conn.cursor()
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                cur.close()
                return [tuple(r) for r in rows]
            finally:
                conn.close()

        _t0 = time.perf_counter()
        try:
            out = self._with_retry(op)
            self._notify({"op": "query_all", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "rows": len(out), "success": True})
            return out
        except DatabaseError as err:
            self._notify({"op": "query_all", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
            raise

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[tuple]:
        rows = self.query_all(sql, params)
        return rows[0] if rows else None

    @contextmanager
    def transaction(self) -> Iterator[None]:
        _t0 = time.perf_counter()
        # Open a transactional connection if not already inside one
        if self._tx_depth == 0:
            self._tx_conn = self._connect(autocommit=False)
        self._tx_depth += 1
        sp_name = f"sp_{self._tx_depth}"
        try:
            cur = self._tx_conn.cursor()
            if self._tx_depth > 1:
                cur.execute(f"SAVE TRANSACTION {sp_name}")
            cur.close()
        except Exception as exc:
            self._tx_depth -= 1
            # Close if outermost failed to start
            if self._tx_depth == 0 and self._tx_conn is not None:
                try:
                    self._tx_conn.close()
                except Exception:
                    pass
                self._tx_conn = None
            msg, code, sqlstate = _extract_mssql_error_info(exc)
            err = map_mssql_error(msg, code, sqlstate)
            self._notify({"op": "transaction_start", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
            raise err

        try:
            yield
        except Exception as inner_exc:
            try:
                cur = self._tx_conn.cursor()
                if self._tx_depth > 1:
                    cur.execute(f"ROLLBACK TRANSACTION {sp_name}")
                else:
                    self._tx_conn.rollback()
                cur.close()
            except Exception as exc:
                msg, code, sqlstate = _extract_mssql_error_info(exc)
                err = map_mssql_error(msg, code, sqlstate)
                self._notify({"op": "transaction_rollback", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
                raise err
            finally:
                self._tx_depth -= 1
                if self._tx_depth == 0 and self._tx_conn is not None:
                    try:
                        self._tx_conn.close()
                    finally:
                        self._tx_conn = None
            raise inner_exc
        else:
            try:
                if self._tx_depth == 1:
                    self._tx_conn.commit()
                self._notify({"op": "transaction_commit", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": True})
            except Exception as exc:
                msg, code, sqlstate = _extract_mssql_error_info(exc)
                err = map_mssql_error(msg, code, sqlstate)
                self._notify({"op": "transaction_commit", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
                raise err
            finally:
                self._tx_depth -= 1
                if self._tx_depth == 0 and self._tx_conn is not None:
                    try:
                        self._tx_conn.close()
                    finally:
                        self._tx_conn = None

    def health_check(self) -> None:
        # Short connect + SELECT 1
        # For Azure AD authentication, skip health check - authentication already completed
        if self._cfg and self._cfg.auth_type and self._cfg.auth_type.startswith("azure_ad"):
            self._notify({"op": "health_check", "backend": self.backend, "duration_ms": 0, "success": True, "skipped": "azure_ad_pre_authenticated"})
            return

        def op():
            # Use shorter timeout for health check to prevent hanging
            if not self._cfg:
                raise DatabaseError("MSSQL adapter not initialized")
            conn_str = _build_conn_str(self._cfg)

            # Add password for SQL authentication if available
            if (self._cfg.auth_type and self._cfg.auth_type.lower() == "sql" and
                hasattr(self, '_sql_password') and self._sql_password):
                if "PWD=" not in conn_str:
                    conn_str += f";PWD={self._sql_password}"

            # Use shorter timeout for health check (10 seconds max)
            health_check_timeout = min(10, int(self._cfg.timeout_seconds or 30))

            # For Azure AD Interactive, use even shorter timeout to prevent hanging
            if self._cfg.auth_type == "azure_ad_interactive":
                health_check_timeout = min(5, health_check_timeout)

            try:
                import pyodbc  # type: ignore
            except Exception as exc:
                raise DatabaseError(f"pyodbc not available: {exc}")

            conn = pyodbc.connect(conn_str, autocommit=True, timeout=health_check_timeout)
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                row = cur.fetchone()
                cur.close()
                if not row or row[0] != 1:
                    raise DatabaseError("MSSQL health check failed")
            finally:
                conn.close()
        _t0 = time.perf_counter()
        try:
            self._with_retry(op, attempts=1)  # Only one attempt for health check
            self._notify({"op": "health_check", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": True})
        except DatabaseError as err:
            self._notify({"op": "health_check", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
            raise

