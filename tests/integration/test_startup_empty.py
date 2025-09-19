from __future__ import annotations

from pathlib import Path

import pytest
from PySide6 import QtWidgets

from src.ui.startup_window import StartupWindow


class _DummyService:
    def create_project(self, *args, **kwargs):  # pragma: no cover - not used
        raise NotImplementedError

    def open_project(self, *args, **kwargs):  # pragma: no cover - not used
        raise NotImplementedError

    def test_mssql_connection(self, *args, **kwargs):  # pragma: no cover - not used
        raise NotImplementedError


@pytest.mark.integration
def test_startup_empty_recent_list_shows_no_entries(qt_app: QtWidgets.QApplication, tmp_path: Path) -> None:
    recent_path = tmp_path / "recent.json"
    window = StartupWindow(_DummyService(), recent_projects_path=recent_path)
    try:
        assert window._recent_list.count() == 0  # type: ignore[attr-defined]
        button_texts = {button.text() for button in window.findChildren(QtWidgets.QPushButton)}
        assert {"Open", "Open...", "Create...", "Clear Recent List"}.issubset(button_texts)
    finally:
        window.deleteLater()
