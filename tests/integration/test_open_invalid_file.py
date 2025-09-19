from __future__ import annotations

from pathlib import Path

import pytest

from src.core.errors import ProjectOpenError
from src.services.migration_service import MigrationService
from src.services.project_service import ProjectService
from src.storage.sqlite_adapter import SQLiteAdapter


def _service(tmp_path: Path) -> ProjectService:
    return ProjectService(
        sqlite_adapter_factory=SQLiteAdapter,
        migration_service_factory=MigrationService,
        recent_projects_path=tmp_path / "recent.json",
    )


@pytest.mark.integration
def test_open_invalid_file_surfaces_error_without_list_update(tmp_path: Path) -> None:
    service = _service(tmp_path)
    invalid_path = tmp_path / "not_a_db.sqlite"
    invalid_path.write_text("not a database", encoding="utf-8")

    with pytest.raises(ProjectOpenError):
        service.open_project(invalid_path)

    assert not (tmp_path / "recent.json").exists()
