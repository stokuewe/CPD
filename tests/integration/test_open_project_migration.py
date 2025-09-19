from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.services.migration_service import MigrationService
from src.services.project_service import ProjectService
from src.storage.sqlite_adapter import SQLiteAdapter


def _service(tmp_path: Path, backup_log: list[tuple[Path, str, str]] | None = None) -> ProjectService:
    recent = tmp_path / "recent.json"

    def backup_warning(path: Path, current: str, target: str) -> None:
        if backup_log is not None:
            backup_log.append((path, current, target))

    return ProjectService(
        sqlite_adapter_factory=SQLiteAdapter,
        migration_service_factory=MigrationService,
        recent_projects_path=recent,
        backup_warning=backup_warning if backup_log is not None else None,
    )


@pytest.mark.integration
def test_open_outdated_project_prompts_backup_and_runs_migrations(tmp_path: Path) -> None:
    backups: list[tuple[Path, str, str]] = []
    service = _service(tmp_path, backups)
    project_path = tmp_path / "project.sqlite"
    service.create_project(project_path, storage_mode="sqlite")

    with sqlite3.connect(project_path) as conn:
        conn.execute("UPDATE meta SET value='0.0.0' WHERE key='schema_version'")
        conn.commit()

    state = service.open_project(project_path)

    assert backups and backups[0][0] == project_path
    assert backups[0][1] == "0.0.0"
    assert state.schema_version == "1.0.0"
