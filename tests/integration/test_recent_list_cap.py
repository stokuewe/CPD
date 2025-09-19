from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.migration_service import MigrationService
from src.services.project_service import ProjectService
from src.storage.sqlite_adapter import SQLiteAdapter


@pytest.mark.integration
def test_recent_projects_list_deduplicates_and_caps_entries(tmp_path: Path) -> None:
    recent = tmp_path / "recent.json"
    service = ProjectService(
        sqlite_adapter_factory=SQLiteAdapter,
        migration_service_factory=MigrationService,
        recent_projects_path=recent,
    )

    paths = []
    for index in range(17):
        project_path = tmp_path / f"project_{index}.sqlite"
        paths.append(project_path)
        service.create_project(project_path, storage_mode="sqlite")

    stored = json.loads(recent.read_text(encoding="utf-8"))
    assert len(stored) == 15
    assert stored[0]["path"].endswith("project_16.sqlite")
    assert stored[-1]["path"].endswith("project_2.sqlite")

    # opening existing project should move it to front without duplicates
    service.open_project(paths[5])
    updated = json.loads(recent.read_text(encoding="utf-8"))
    assert updated[0]["path"].endswith("project_5.sqlite")
    assert len({item["path"] for item in updated}) == len(updated)
