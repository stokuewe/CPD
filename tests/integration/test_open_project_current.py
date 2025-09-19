from __future__ import annotations

from pathlib import Path

import pytest

from src.services.migration_service import MigrationService
from src.services.project_service import ProjectService
from src.storage.sqlite_adapter import SQLiteAdapter


def _service(tmp_path: Path) -> ProjectService:
    recent = tmp_path / "recent.json"
    return ProjectService(
        sqlite_adapter_factory=SQLiteAdapter,
        migration_service_factory=MigrationService,
        recent_projects_path=recent,
    )


@pytest.mark.integration
def test_open_project_with_current_schema_succeeds_without_migration(tmp_path: Path) -> None:
    service = _service(tmp_path)
    project_path = tmp_path / "project.sqlite"
    service.create_project(project_path, storage_mode="sqlite")

    state = service.open_project(project_path)

    assert state.schema_version == "1.0.0"
    assert state.storage_mode == "sqlite"
    assert not state.read_only
