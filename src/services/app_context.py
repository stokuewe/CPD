from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.services.database_gateway import DatabaseGateway, GatewayConfig, DatabaseError
from src.services.db_adapters.sqlite_adapter import SqliteAdapter
from src.services.db_adapters.mssql_adapter import MssqlAdapter


@dataclass
class ProjectRuntime:
    sqlite_path: Path
    storage_mode: str  # 'sqlite' | 'mssql'


class AppContext:
    """Global application context for active project and DatabaseGateway.

    This holds the active settings SQLite path and a DatabaseGateway configured per
    constitution: long-lived SQLite connection for local mode, per-operation MSSQL
    connections for remote mode.
    """

    def __init__(self) -> None:
        self._project: Optional[ProjectRuntime] = None
        self._gateway: Optional[DatabaseGateway] = None
        self._pending_schema_validation: Optional[dict] = None

    @property
    def project(self) -> Optional[ProjectRuntime]:
        return self._project

    @property
    def gateway(self) -> Optional[DatabaseGateway]:
        return self._gateway

    def close(self) -> None:
        # Clear stored password for security
        if self._project and self._project.storage_mode == "mssql":
            try:
                from src.services.secure_credential_manager import get_credential_manager
                credential_manager = get_credential_manager()
                credential_manager.clear_password(str(self._project.sqlite_path))
            except Exception:
                pass  # Ignore cleanup errors

        if self._gateway is not None:
            try:
                self._gateway.close()
            except Exception:
                pass
            finally:
                self._gateway = None
        self._project = None

    def load_project(self, sqlite_settings_path: str | Path) -> None:
        """Load project by settings file and initialize DatabaseGateway accordingly."""
        p = Path(sqlite_settings_path)
        if not p.exists():
            raise FileNotFoundError(p)

        # Close current
        self.close()

        storage_mode = self._read_storage_mode(p) or "sqlite"
        self._project = ProjectRuntime(sqlite_path=p, storage_mode=storage_mode)

        if storage_mode == "sqlite":
            gw = SqliteAdapter()
            gw.init(GatewayConfig(backend="sqlite", sqlite_path=str(p)))
            # Health check implicit via init; can run an explicit check too
            gw.health_check()
            self._gateway = gw
            return

        if storage_mode == "mssql":
            server, database, auth_type, username, authority, timeout, use_driver17 = self._read_remote_descriptor(p)

            # For SQL authentication, get password from secure credential manager
            password = None
            if auth_type.lower() == "sql":
                from src.services.secure_credential_manager import get_credential_manager
                credential_manager = get_credential_manager()
                password = credential_manager.get_password(str(p))

            gw = MssqlAdapter()
            gw.init(
                GatewayConfig(
                    backend="mssql",
                    server=server,
                    database=database,
                    auth_type=auth_type,
                    username=username,
                    authority=authority,
                    timeout_seconds=timeout,
                    use_driver17=use_driver17,
                ),
                sql_password=password  # Pass password securely to adapter
            )
            # Skip health check for Azure AD - authentication already completed in main thread
            if auth_type.startswith("azure_ad"):
                print(f"DEBUG: Skipping health check for Azure AD authentication")
            else:
                print(f"DEBUG: Running health check for {auth_type}")
                gw.health_check()
                print(f"DEBUG: Health check completed")

            # Validate schema after successful connection
            print(f"DEBUG: About to validate remote schema for {p}")
            self._validate_remote_schema(gw, str(p))
            print(f"DEBUG: Schema validation completed for {p}")

            self._gateway = gw
            return

        raise DatabaseError(f"Unknown storage_mode: {storage_mode}")

    def _validate_remote_schema(self, gateway: DatabaseGateway, project_path: str) -> None:
        """Validate remote database schema and handle user interaction"""
        from src.services.schema_validator import SchemaValidator

        validator = SchemaValidator(gateway)
        result = validator.validate_schema()

        if result.is_valid:
            # Schema is valid - continue
            return

        # Schema validation failed or needs attention - this will be handled by the UI thread
        # Store the validation result for the UI to handle
        self._pending_schema_validation = {
            'validator': validator,
            'result': result,
            'project_path': project_path
        }

        # Raise an exception that the UI can catch and handle appropriately
        print(f"DEBUG: About to raise schema validation exception")
        if result.error_message:
            print(f"DEBUG: Raising error for error_message: {result.error_message}")
            raise DatabaseError(f"Schema validation error: {result.error_message}")
        elif result.has_no_tables:
            print(f"DEBUG: Raising SCHEMA_DEPLOYMENT_REQUIRED")
            raise DatabaseError("SCHEMA_DEPLOYMENT_REQUIRED")
        else:
            print(f"DEBUG: Raising SCHEMA_DEVIATIONS_DETECTED")
            raise DatabaseError("SCHEMA_DEVIATIONS_DETECTED")

    def get_pending_schema_validation(self) -> Optional[dict]:
        """Get pending schema validation data for UI handling"""
        return self._pending_schema_validation

    def clear_pending_schema_validation(self) -> None:
        """Clear pending schema validation data"""
        self._pending_schema_validation = None

    def handle_schema_deployment(self) -> None:
        """Deploy schema using pending validation data"""
        if not self._pending_schema_validation:
            raise ValueError("No pending schema validation")

        validator = self._pending_schema_validation['validator']
        validator.deploy_schema()

        # Clear pending validation
        self._pending_schema_validation = None

    # Internal helpers -------------------------------------------------
    def _read_storage_mode(self, path: Path) -> Optional[str]:
        try:
            with sqlite3.connect(path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute("SELECT value FROM settings WHERE key='storage_mode'")
                row = cur.fetchone()
                return (row[0] if row else None) or None
        except Exception:
            return None

    def _read_remote_descriptor(self, path: Path):
        # Defaults
        server = database = auth_type = username = authority = ""
        port = 1433
        timeout = 30
        use_driver17 = False
        try:
            with sqlite3.connect(path) as conn:
                conn.row_factory = sqlite3.Row
                def _get(k: str) -> Optional[str]:
                    r = conn.execute("SELECT value FROM settings WHERE key=?", (k,)).fetchone()
                    return r[0] if r else None
                server = _get("remote_server") or ""
                database = _get("remote_database") or ""
                auth_type = (_get("remote_auth_type") or "windows").lower()
                username = _get("remote_username") or ""
                authority = _get("remote_authority") or ""
                p = _get("remote_port")
                if p and str(p).isdigit():
                    port = int(p)
                t = _get("remote_timeout_seconds")
                if t and str(t).isdigit():
                    timeout = int(t)
                d17 = _get("remote_use_driver17")
                if d17 and str(d17) in ("1", "true", "True"):
                    use_driver17 = True
        except Exception:
            pass
        # Embed port into server if provided (e.g., server,port)
        if server and "," not in server and port:
            server = f"{server},{port}"
        return server, database, auth_type, username, authority, timeout, use_driver17

    # Public settings helpers -----------------------------------------
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if not self._project:
            return default
        try:
            with sqlite3.connect(self._project.sqlite_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
                return (row[0] if row else None) or default
        except Exception:
            return default

    def set_setting(self, key: str, value: str) -> None:
        if not self._project:
            raise RuntimeError("No project loaded")
        with sqlite3.connect(self._project.sqlite_path) as conn:
            conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, value))
            conn.commit()



# Singleton instance for easy import
app_context = AppContext()

