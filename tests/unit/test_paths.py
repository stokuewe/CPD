from __future__ import annotations

import os
from pathlib import Path

from src.lib.paths import ensure_user_app_data_dir, recent_projects_path, normalize_project_path, is_unc_path


def test_appdata_and_recent_path(monkeypatch, tmp_path):
    # Simulate a clean APPDATA location
    fake_appdata = tmp_path / "AppDataRoaming"
    monkeypatch.setenv("APPDATA", str(fake_appdata))

    app_dir = ensure_user_app_data_dir()
    assert app_dir == Path(fake_appdata) / "CPD"
    assert app_dir.exists()

    recent = recent_projects_path()
    assert recent.parent == app_dir
    assert recent.name == "recent_projects.json"


def test_normalize_and_unc():
    a = normalize_project_path("C:/Temp/FILE.sqlite")
    b = normalize_project_path("c:/temp/file.sqlite")
    assert a == b  # case-insensitive normalization on Windows

    unc = r"\\server\share\folder\proj.sqlite"
    assert is_unc_path(unc)
    assert not is_unc_path("C:/Projects/proj.sqlite")

