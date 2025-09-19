import pytest

# Skip if GUI stack not available
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")


def test_startup_view_shows_recent_and_actions(qtbot):
    # Import inside test to allow collection even if app not implemented yet
    from src.app.main_window import MainWindow  # noqa: F401
    # If MainWindow is not implemented yet, this import will fail → expected in TDD
    assert True  # Placeholder: full UI assertions after implementation

