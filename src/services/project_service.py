from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Mapping, MutableMapping, Optional

from src.core.errors import (
    ConnectionAuthenticationError,
    ConnectionFailureError,
    ConnectionTimeoutError,
    MigrationBlockedError,
    ProjectCreationError,
    ProjectOpenError,
    UserFacingError,
)
from src.services.migration_service import MigrationService, TARGET_SCHEMA_VERSION
from src.services.recent_projects import RecentProjectEntry, add_entry, load_once, save
from src.storage.adapter import StorageAdapter
from src.storage.mssql_adapter import MSSQLAdapter, MSSQLProfile
from src.storage.sqlite_adapter import SQLiteAdapter

BackupWarning = Callable[[Path, str, str], None]


@dataclass(slots=True)
class ProjectState:
    settings_path: Path
    storage_mode: Literal["sqlite", "mssql"]
    schema_version: str
    read_only: bool
    opened_at: datetime
    connection_profile: Mapping[str, object] | None = None


class ProjectService:
    """Coordinates project creation and opening workflows."""

    def __init__(
        self,
        *,
        sqlite_adapter_factory: Callable[[Path], SQLiteAdapter],
        migration_service_factory: Callable[[StorageAdapter], MigrationService],
        recent_projects_path: Path,
        backup_warning: BackupWarning | None = None,
        mssql_adapter_factory: Callable[[MSSQLProfile], MSSQLAdapter] | None = None,
    ) -> None:
        self._sqlite_adapter_factory = sqlite_adapter_factory
        self._migration_service_factory = migration_service_factory
        self._recent_projects_path = recent_projects_path
        self._backup_warning = backup_warning
        self._mssql_adapter_factory = mssql_adapter_factory or (lambda profile: MSSQLAdapter(profile))
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        self._state: ProjectState | None = None

    @property
    def state(self) -> ProjectState | None:
        return self._state

    def create_project(
        self,
        settings_path: Path,
        *,
        storage_mode: Literal["sqlite", "mssql"],
        mssql_profile: Optional[dict[str, object]] = None,
    ) -> ProjectState:
        context = self._operation_context("create_project", settings_path, mode=storage_mode)
        self._logger.info("Creating project", extra=context)
        with self._lock:
            try:
                state = self._create_locked(settings_path, storage_mode, mssql_profile)
            except UserFacingError:
                self._logger.error("Project creation failed", extra=context, exc_info=True)
                raise
            except Exception as exc:
                self._logger.error("Project creation failed", extra=context, exc_info=True)
                raise ProjectCreationError(
                    "Project creation failed due to an unexpected error.",
                    title="Project Creation Failed",
                    remediation="Verify you have write access to the chosen folder and retry.",
                ) from exc
            else:
                self._logger.info(
                    "Project created",
                    extra={
                        **context,
                        "schema_version": state.schema_version,
                        "read_only": state.read_only,
                    },
                )
                return state

    def open_project(self, settings_path: Path) -> ProjectState:
        context = self._operation_context("open_project", settings_path)
        self._logger.info("Opening project", extra=context)
        if not settings_path.exists():
            error = ProjectOpenError(
                f"Project not found at {settings_path}.",
                title="Project Not Found",
                remediation="Select an existing project file or create a new project.",
            )
            self._logger.warning("Project file missing", extra=context)
            raise error
        with self._lock:
            try:
                state = self._open_locked(settings_path)
            except (UserFacingError, MigrationBlockedError):
                self._logger.error("Project open failed", extra=context, exc_info=True)
                raise
            except Exception as exc:
                self._logger.error("Project open failed", extra=context, exc_info=True)
                raise ProjectOpenError(
                    "Failed to open the project due to an unexpected error.",
                    title="Project Open Failed",
                    remediation="Ensure the file is a valid CPD settings database and is not locked by another process.",
                ) from exc
            else:
                self._logger.info(
                    "Project opened",
                    extra={
                        **context,
                        "schema_version": state.schema_version,
                        "storage_mode": state.storage_mode,
                        "read_only": state.read_only,
                    },
                )
                return state

    def test_mssql_connection(self, raw_profile: dict[str, object]) -> None:
        context = {
            "operation": "test_connection",
            "server": str(raw_profile.get("server", "")),
            "database": str(raw_profile.get("database", "")),
        }
        self._logger.info("Testing MSSQL connection", extra=context)
        try:
            profile = self._coerce_profile(raw_profile)
        except ValueError as exc:
            self._logger.warning("Invalid MSSQL parameters", extra=context, exc_info=True)
            raise ConnectionFailureError(
                "Connection parameters are incomplete.",
                title="Invalid Connection Parameters",
                remediation="Provide server, database, and authentication details before retrying the test.",
            ) from exc

        adapter = self._mssql_adapter_factory(profile)
        try:
            adapter.test_connection()
        except (
            ConnectionTimeoutError,
            ConnectionAuthenticationError,
            ConnectionFailureError,
        ):
            self._logger.warning("MSSQL connection test failed", extra=context, exc_info=True)
            raise
        except Exception as exc:
            self._logger.error("MSSQL connection test failed", extra=context, exc_info=True)
            raise ConnectionFailureError(
                "Unexpected MSSQL connection failure.",
                title="Connection Failed",
                remediation="Verify network connectivity and SQL Server availability, then retry.",
            ) from exc
        finally:
            adapter.close()
        self._logger.info("MSSQL connection test succeeded", extra=context)

    def _create_locked(
        self,
        settings_path: Path,
        storage_mode: Literal["sqlite", "mssql"],
        mssql_profile: Optional[dict[str, object]],
    ) -> ProjectState:
        if storage_mode not in {"sqlite", "mssql"}:
            raise ProjectCreationError(
                f"Unsupported storage mode '{storage_mode}'.",
                title="Invalid Storage Mode",
                remediation="Choose either SQLite (local) or MSSQL (remote).",
            )
        if settings_path.exists():
            raise ProjectCreationError(
                f"The selected file already exists: {settings_path}.",
                title="File Already Exists",
                remediation="Choose a new file name or remove the existing file before creating the project.",
            )

        profile: MSSQLProfile | None = None
        if storage_mode == "mssql":
            try:
                profile = self._coerce_profile(mssql_profile)
            except ValueError as exc:
                raise ProjectCreationError(
                    "MSSQL configuration is incomplete.",
                    title="Invalid MSSQL Configuration",
                    remediation="Provide server, database, and authentication details before creating the project.",
                ) from exc

        adapter = self._sqlite_adapter_factory(settings_path)
        migration_service = self._migration_service_factory(adapter)
        try:
            migration_service.run_migrations(settings_path)
            self._seed_settings(adapter, storage_mode, settings_path)
            if profile:
                self._store_mssql_profile(adapter, profile)
        except MigrationBlockedError:
            self._safe_unlink(settings_path)
            raise
        except UserFacingError:
            self._safe_unlink(settings_path)
            raise
        except Exception as exc:
            self._safe_unlink(settings_path)
            raise ProjectCreationError(
                "Failed to initialize the project database.",
                title="Project Creation Failed",
                remediation="Ensure the destination is writable and retry.",
            ) from exc
        finally:
            adapter.close()

        read_only = False
        if profile:
            read_only = not self._probe_remote(profile)

        state = ProjectState(
            settings_path=settings_path,
            storage_mode=storage_mode,
            schema_version=TARGET_SCHEMA_VERSION,
            read_only=read_only,
            opened_at=datetime.now(timezone.utc),
            connection_profile=self._sanitize_profile(profile),
        )
        self._state = state
        self._update_recent_projects(settings_path)
        return state

    def _open_locked(self, settings_path: Path) -> ProjectState:
        adapter = self._sqlite_adapter_factory(settings_path)
        migration_service = self._migration_service_factory(adapter)
        profile: MSSQLProfile | None = None
        read_only = False
        try:
            schema_version = migration_service.check_version(settings_path)
            if schema_version != TARGET_SCHEMA_VERSION and self._backup_warning:
                self._backup_warning(settings_path, schema_version, TARGET_SCHEMA_VERSION)
            if schema_version != TARGET_SCHEMA_VERSION:
                schema_version = migration_service.run_migrations(settings_path)

            settings_map = self._load_settings(adapter)
            storage_mode = self._resolve_storage_mode(settings_map)
            if storage_mode == "mssql":
                profile = self._load_mssql_profile(adapter)
        except (MigrationBlockedError, UserFacingError):
            raise
        except Exception as exc:
            raise ProjectOpenError(
                "Failed to prepare project for opening.",
                title="Project Open Failed",
                remediation="Ensure the file is a valid CPD project and retry.",
            ) from exc
        finally:
            adapter.close()

        if storage_mode == "mssql" and profile:
            read_only = not self._probe_remote(profile)

        state = ProjectState(
            settings_path=settings_path,
            storage_mode=storage_mode,
            schema_version=schema_version,
            read_only=read_only,
            opened_at=datetime.now(timezone.utc),
            connection_profile=self._sanitize_profile(profile),
        )
        self._state = state
        self._update_recent_projects(settings_path)
        return state

    def _seed_settings(
        self,
        adapter: SQLiteAdapter,
        storage_mode: Literal["sqlite", "mssql"],
        settings_path: Path,
    ) -> None:
        project_name = settings_path.stem
        created_at = datetime.now(timezone.utc).isoformat()
        adapter.begin()
        try:
            for key, value in (
                ("project_name", project_name),
                ("storage_mode", storage_mode),
                ("created_at", created_at),
            ):
                adapter.execute(
                    """
                    INSERT INTO settings(key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, value),
                )
            adapter.commit()
        except Exception:
            adapter.rollback()
            raise

    def _store_mssql_profile(self, adapter: SQLiteAdapter, profile: MSSQLProfile) -> None:
        adapter.begin()
        try:
            adapter.execute(
                """
                INSERT INTO mssql_connection(id, server, database, port, auth_type, username, password)
                VALUES (1, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(id) DO UPDATE SET
                    server = excluded.server,
                    database = excluded.database,
                    port = excluded.port,
                    auth_type = excluded.auth_type,
                    username = excluded.username,
                    password = NULL
                """,
                (
                    profile.server,
                    profile.database,
                    profile.port or 1433,
                    profile.auth_type,
                    profile.username,
                ),
            )
            adapter.commit()
        except Exception:
            adapter.rollback()
            raise

    def _load_settings(self, adapter: SQLiteAdapter) -> MutableMapping[str, str]:
        rows = adapter.query("SELECT key, value FROM settings")
        if not rows:
            raise ProjectOpenError(
                "Project settings table is missing required entries.",
                title="Invalid Project",
                remediation="Restore from backup or recreate the project.",
            )
        return {str(row["key"]): str(row["value"]) for row in rows}

    def _resolve_storage_mode(self, settings_map: Mapping[str, str]) -> Literal["sqlite", "mssql"]:
        mode = settings_map.get("storage_mode")
        if mode not in {"sqlite", "mssql"}:
            raise ProjectOpenError(
                "Project storage mode could not be determined.",
                title="Invalid Project",
                remediation="The project may be corrupted; restore from backup or recreate it.",
            )
        return mode  # type: ignore[return-value]

    def _load_mssql_profile(self, adapter: SQLiteAdapter) -> MSSQLProfile:
        rows = adapter.query(
            "SELECT server, database, port, auth_type, username FROM mssql_connection WHERE id = 1"
        )
        if not rows:
            raise ProjectOpenError(
                "Remote project is missing connection information.",
                title="Incomplete Project",
                remediation="Recreate the project or re-enter MSSQL connection details.",
            )
        row = rows[0]
        port = row.get("port")
        port_value = int(port) if port is not None else None
        return MSSQLProfile(
            server=str(row["server"]),
            database=str(row["database"]),
            auth_type=str(row["auth_type"]),
            username=row.get("username"),
            port=port_value,
        )

    def _probe_remote(self, profile: MSSQLProfile) -> bool:
        context = {
            "operation": "probe_mssql",
            "server": profile.server,
            "database": profile.database,
        }
        adapter = self._mssql_adapter_factory(profile)
        try:
            adapter.test_connection()
        except (
            ConnectionTimeoutError,
            ConnectionAuthenticationError,
            ConnectionFailureError,
        ):
            self._logger.warning("MSSQL connection unavailable", extra=context, exc_info=True)
            return False
        except Exception:
            self._logger.warning("MSSQL connection unavailable", extra=context, exc_info=True)
            return False
        finally:
            adapter.close()
        self._logger.info("MSSQL connection confirmed", extra=context)
        return True

    def _update_recent_projects(self, settings_path: Path) -> None:
        entries = load_once(self._recent_projects_path)
        updated = add_entry(
            entries,
            RecentProjectEntry(path=settings_path, last_opened=datetime.now(timezone.utc)),
        )
        save(self._recent_projects_path, updated)

    def _sanitize_profile(self, profile: MSSQLProfile | None) -> Mapping[str, object] | None:
        if profile is None:
            return None
        return {
            "server": profile.server,
            "database": profile.database,
            "auth_type": profile.auth_type,
            "username": profile.username,
            "port": profile.port,
        }

    def _coerce_profile(self, raw: Optional[dict[str, object]]) -> MSSQLProfile:
        if raw is None:
            raise ValueError("MSSQL profile required for remote projects")
        server_value = raw.get("server")
        database_value = raw.get("database")
        auth_type_value = raw.get("auth_type", "sql")
        username_value = raw.get("username")
        password_value = raw.get("password")
        port_value = raw.get("port")
        driver_value = raw.get("driver", "ODBC Driver 18 for SQL Server")
        if not server_value or not database_value:
            raise ValueError("MSSQL profile must specify server and database")
        server = str(server_value)
        database = str(database_value)
        auth_type = str(auth_type_value).lower()
        if auth_type not in {"sql", "windows"}:
            raise ValueError("MSSQL profile auth_type must be 'sql' or 'windows'")
        username = str(username_value) if username_value else None
        password = str(password_value) if password_value else None
        port = int(port_value) if port_value is not None else None
        driver = str(driver_value)
        return MSSQLProfile(
            server=server,
            database=database,
            auth_type=auth_type,
            username=username,
            password=password,
            port=port,
            driver=driver,
        )

    def _operation_context(self, operation: str, path: Path, **extra: object) -> dict[str, object]:
        context: dict[str, object] = {"operation": operation, "path": str(path)}
        context.update(extra)
        return context

    def _safe_unlink(self, path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            return
        except OSError:
            self._logger.warning(
                "Failed to remove incomplete project file",
                extra={"operation": "cleanup", "path": str(path)},
                exc_info=True,
            )


__all__ = ["ProjectService", "ProjectState", "BackupWarning"]
