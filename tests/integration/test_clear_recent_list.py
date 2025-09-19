from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PySide6 import QtWidgets

from src.services.recent_projects import RecentProjectEntry
from src.ui import message_dialogs
from src.ui.startup_window import StartupWindow


class _DummyService:
    def create_project(self, *args, **kwargs):  # pragma: no cover - not used
        raise NotImplementedError

    def open_project(self, *args, **kwargs):  # pragma: no cover - not used
        raise NotImplementedError

    def test_mssql_connection(self, *args, **kwargs):  # pragma: no cover - not used
        raise NotImplementedError


@pytest.mark.integration
def test_clear_recent_projects_action_persists_empty_list(
    qt_app: QtWidgets.QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recent_path = tmp_path / "recents.json"
    entries = [
        RecentProjectEntry(path=tmp_path / f"project_{idx}.sqlite", last_opened=datetime.now(timezone.utc)).as_payload()
        for idx in range(3)
    ]
    recent_path.write_text(json.dumps(entries), encoding="utf-8")

    window = StartupWindow(_DummyService(), recent_projects_path=recent_path)
    try:
        assert window._recent_list.count() == 3  # type: ignore[attr-defined]
        monkeypatch.setattr(message_dialogs, "ask_confirmation", lambda *_, **__: True)

        window._clear_recent_list()

        assert window._recent_list.count() == 0  # type: ignore[attr-defined]
        assert json.loads(recent_path.read_text(encoding="utf-8")) == []
    finally:
        window.deleteLater()
