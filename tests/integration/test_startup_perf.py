import os
import time
from pathlib import Path

import pytest
from PySide6 import QtWidgets

from src.ui.startup_window import StartupWindow


ios_env_platform = "QT_QPA_PLATFORM"
os.environ.setdefault(ios_env_platform, os.environ.get(ios_env_platform, "offscreen"))


@pytest.fixture(scope="module")
def qt_app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class DummyProjectService:
    def create_project(self, *_, **__):  # pragma: no cover - not used in perf smoke
        raise NotImplementedError

    def open_project(self, *_args, **_kwargs):  # pragma: no cover - not used in perf smoke
        raise NotImplementedError

    def test_mssql_connection(self, *_args, **_kwargs):  # pragma: no cover
        raise NotImplementedError


@pytest.mark.performance
@pytest.mark.integration
def test_startup_window_constructs_under_half_second(qt_app: QtWidgets.QApplication, tmp_path: Path) -> None:
    service = DummyProjectService()
    start = time.perf_counter()
    window = StartupWindow(service, recent_projects_path=tmp_path / "recent.json")
    elapsed = time.perf_counter() - start
    try:
        assert elapsed < 0.5, f"StartupWindow took {elapsed:.3f}s to construct"
    finally:
        window.deleteLater()
