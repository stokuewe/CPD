import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")


def test_create_project_local_flow(qtbot, tmp_path):
    from src.app.controllers.startup_controller import StartupController  # noqa: F401
    # Placeholder: after implementation, assert new sqlite project is created and appears in recent list
    assert True

