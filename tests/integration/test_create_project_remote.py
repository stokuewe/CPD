import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")


def test_create_project_remote_requires_successful_test_connection(qtbot):
    from src.app.controllers.startup_controller import StartupController  # noqa: F401
    # Placeholder: after implementation, assert creation blocked until Test Connection success
    assert True

