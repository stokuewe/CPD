from __future__ import annotations

import json
import sqlite3
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
def test_create_local_project_flow_baseline_schema(tmp_path: Path) -> None:
    service = _service(tmp_path)
    project_path = tmp_path / "project.sqlite"

    state = service.create_project(project_path, storage_mode="sqlite")

    assert project_path.exists()
    assert state.schema_version == "1.0.0"
    assert not state.read_only

    with sqlite3.connect(project_path) as conn:
        value = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        assert value == ("1.0.0",)

    recents = json.loads((tmp_path / "recent.json").read_text(encoding="utf-8"))
    assert recents[0]["path"].endswith("project.sqlite")
    assert len(recents) == 1
