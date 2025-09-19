from __future__ import annotations

from pathlib import Path

import pytest

from src.core.errors import ConnectionTimeoutError
from src.services.migration_service import MigrationService
from src.services.project_service import ProjectService
from src.storage.mssql_adapter import MSSQLAdapter, MSSQLProfile
from src.storage.sqlite_adapter import SQLiteAdapter


class FailingMSSQLAdapter(MSSQLAdapter):
    def __init__(self, profile: MSSQLProfile) -> None:
        # Do not call parent constructor to avoid pyodbc dependency during tests
        self._profile = profile

    def test_connection(self) -> None:
        raise ConnectionTimeoutError(
            "Simulated timeout",
            title="Timeout",
            remediation="retry",
        )

    def close(self) -> None:  # pragma: no cover - nothing to close
        return None


@pytest.mark.integration
def test_remote_project_open_enters_read_only_when_mssql_unreachable(tmp_path: Path) -> None:
    recent = tmp_path / "recents.json"

    def mssql_factory(profile: MSSQLProfile) -> MSSQLAdapter:
        return FailingMSSQLAdapter(profile)

    service = ProjectService(
        sqlite_adapter_factory=SQLiteAdapter,
        migration_service_factory=MigrationService,
        recent_projects_path=recent,
        mssql_adapter_factory=mssql_factory,
    )
    project_path = tmp_path / "remote.sqlite"

    service.create_project(
        project_path,
        storage_mode="mssql",
        mssql_profile={
            "server": "localhost",
            "database": "demo",
            "auth_type": "sql",
            "username": "user",
            "password": "pass",
        },
    )

    state = service.open_project(project_path)
    assert state.storage_mode == "mssql"
    assert state.read_only
