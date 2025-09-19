import json
import os
from pathlib import Path
import pytest


def test_recent_projects_behaviors(tmp_path, monkeypatch):
    # Arrange: route recent projects file to a temp location
    recent_path = tmp_path / "recent_projects.json"

    # Late import pattern (to allow file to collect even if module missing)
    try:
        from src.services.recent_projects import RecentProjectsService
        from src.lib import paths as paths_mod
    except Exception:
        # Force a failure consistent with TDD if service not implemented yet
        pytest.fail("RecentProjectsService not implemented yet")

    monkeypatch.setattr(paths_mod, "recent_projects_path", lambda: recent_path)

    svc = RecentProjectsService()

    # Start with empty list
    svc.clear()
    assert recent_path.exists()
    assert svc.list() == []

    # Add entries and verify move-to-top + de-dup + cap=10
    for i in range(12):
        p = tmp_path / f"proj{i}.sqlite"
        p.write_text("test")
        svc.add(str(p))

    entries = svc.list()
    assert len(entries) == 10  # cap applied
    # Most recent at top
    assert Path(entries[0]["path"]).name == "proj11.sqlite"

    # Re-add an existing path -> moved to top, no duplicates
    svc.add(str(tmp_path / "proj5.sqlite"))
    entries2 = svc.list()
    assert len(entries2) == 10
    assert Path(entries2[0]["path"]).name == "proj5.sqlite"

    # Simulate a missing file in stored list -> drop on load
    # Manually write an entry to file for a missing path
    data = svc.list()
    data.append({"path": str(tmp_path / "does_not_exist.sqlite"), "last_opened": "2025-01-01T00:00:00"})
    recent_path.write_text(json.dumps(data))
    svc.reload()
    assert all(Path(e["path"]).exists() for e in svc.list())

