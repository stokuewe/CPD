from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence

from src.services.database_gateway import (
    DatabaseGateway,
    GatewayConfig,
    map_sqlite_exception,
    DatabaseError,
)


class SqliteAdapter(DatabaseGateway):
    """SQLite implementation of DatabaseGateway.

    - Opens one long-lived connection on init()
    - Enables PRAGMAs per constitution: foreign_keys=ON, journal_mode=WAL, synchronous=NORMAL
    - Provides savepoint-based transaction() with support for nesting
    """

    def __init__(self) -> None:
        super().__init__()
        self._backend = "sqlite"
        self._conn: Optional[sqlite3.Connection] = None
        self._tx_depth = 0

    def _ensure_conn(self) -> sqlite3.Connection:
        if not self._conn:
            raise DatabaseError("SQLite adapter not initialized")
        return self._conn

    def init(self, cfg: GatewayConfig) -> None:
        if cfg.backend != "sqlite":
            raise DatabaseError("SqliteAdapter requires backend='sqlite'")
        if not cfg.sqlite_path:
            raise DatabaseError("sqlite_path is required for SqliteAdapter")

        # Long-lived connection; manual transaction control
        try:
            conn = sqlite3.connect(
                cfg.sqlite_path,
                timeout=30.0,
                isolation_level=None,  # autocommit mode; we manage transactions explicitly
                check_same_thread=False,  # allow usage from worker threads when needed
            )
            # Return plain tuples (not Row) to keep interface consistent
            conn.row_factory = None
            # PRAGMAs
            conn.execute("PRAGMA foreign_keys=ON")
            # journal_mode returns a row; ensure WAL attempted
            conn.execute("PRAGMA journal_mode=WAL").fetchone()
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
        except Exception as exc:
            raise map_sqlite_exception(exc)

        self._conn = conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            finally:
                self._conn = None

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        conn = self._ensure_conn()
        _t0 = time.perf_counter()
        try:
            cur = conn.execute(sql, tuple(params))
            rc = cur.rowcount if cur.rowcount is not None else -1
            rc2 = 0 if rc is None or rc < 0 else int(rc)
            self._notify({"op": "execute", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "rowcount": rc2, "success": True})
            return rc2
        except Exception as exc:
            err = map_sqlite_exception(exc)
            self._notify({"op": "execute", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
            raise err

    def query_all(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        conn = self._ensure_conn()
        _t0 = time.perf_counter()
        try:
            cur = conn.execute(sql, tuple(params))
            rows = cur.fetchall()
            out = [tuple(r) for r in rows]
            self._notify({"op": "query_all", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "rows": len(out), "success": True})
            return out
        except Exception as exc:
            err = map_sqlite_exception(exc)
            self._notify({"op": "query_all", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
            raise err

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[tuple]:
        conn = self._ensure_conn()
        _t0 = time.perf_counter()
        try:
            cur = conn.execute(sql, tuple(params))
            row = cur.fetchone()
            out = tuple(row) if row is not None else None
            self._notify({"op": "query_one", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "rows": 1 if out is not None else 0, "success": True})
            return out
        except Exception as exc:
            err = map_sqlite_exception(exc)
            self._notify({"op": "query_one", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
            raise err

    @contextmanager
    def transaction(self) -> Iterator[None]:
        conn = self._ensure_conn()
        _t0 = time.perf_counter()
        self._tx_depth += 1
        sp_name = f"sp_{self._tx_depth}"
        try:
            conn.execute(f"SAVEPOINT {sp_name}")
        except Exception as exc:
            self._tx_depth -= 1
            err = map_sqlite_exception(exc)
            self._notify({"op": "transaction_start", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
            raise err
        try:
            yield
        except Exception as inner_exc:
            try:
                conn.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                conn.execute(f"RELEASE SAVEPOINT {sp_name}")
            except Exception as exc:
                err = map_sqlite_exception(exc)
                self._notify({"op": "transaction_rollback", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
                raise err
            finally:
                self._tx_depth -= 1
            # Propagate original error after notifying rollback
            raise inner_exc
        else:
            try:
                conn.execute(f"RELEASE SAVEPOINT {sp_name}")
                self._notify({"op": "transaction_commit", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": True})
            except Exception as exc:
                err = map_sqlite_exception(exc)
                self._notify({"op": "transaction_commit", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
                raise err
            finally:
                self._tx_depth -= 1

    def health_check(self) -> None:
        conn = self._ensure_conn()
        _t0 = time.perf_counter()
        try:
            row = conn.execute("SELECT 1").fetchone()
            if not row or row[0] != 1:
                raise DatabaseError("SQLite health check failed")
            self._notify({"op": "health_check", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": True})
        except Exception as exc:
            err = map_sqlite_exception(exc)
            self._notify({"op": "health_check", "backend": self.backend, "duration_ms": (time.perf_counter() - _t0) * 1000, "success": False, "error_class": err.__class__.__name__, "error_message": str(err)[:200]})
            raise err

