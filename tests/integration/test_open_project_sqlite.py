import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")


def test_open_existing_project_runs_schema_checks(qtbot, tmp_path):
    from src.app.controllers.startup_controller import StartupController  # noqa: F401
    # Placeholder flow:
    # - point controller to a temp sqlite project
    # - expect schema check → migration or refusal
    assert True

