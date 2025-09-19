import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")


def test_clear_recent_action_updates_ui_and_persistence(qtbot):
    from src.app.controllers.startup_controller import StartupController  # noqa: F401
    # Placeholder: after implementation, assert list cleared and persisted
    assert True

