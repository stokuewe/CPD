import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")


def test_open_button_shows_dialog_when_no_selection(qtbot, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt
    from src.app.main_window import MainWindow
    from src.app.controllers.startup_controller import StartupController
    from src.lib import paths as paths_mod

    # Route recent storage to temp file
    recent_path = tmp_path / "recent_projects.json"
    monkeypatch.setattr(paths_mod, "recent_projects_path", lambda: recent_path)

    # Prepare controller + window
    controller = StartupController()
    win = MainWindow()
    controller.attach_view(win)
    qtbot.addWidget(win)
    win.show()

    # Create some recent entries but ensure no selection is active
    p1 = tmp_path / "a.sqlite"; p1.write_text("x")
    p2 = tmp_path / "b.sqlite"; p2.write_text("x")
    controller.recent_service.clear()
    controller.recent_service.add(str(p1))
    controller.recent_service.add(str(p2))
    win.show_recent(controller.recent_service.list())
    win.recent_list.clearSelection(); win.recent_list.setCurrentRow(-1)

    # Spy: ensure file dialog is invoked and open_project is NOT called when dialog canceled
    called = {"dlg": False, "open": []}

    def fake_get_open_file_name(parent=None, caption=None, dir=None, filter=None):
        called["dlg"] = True
        return "", ""

    from PySide6.QtWidgets import QFileDialog
    monkeypatch.setattr(QFileDialog, "getOpenFileName", fake_get_open_file_name)
    controller.open_project = lambda path: called["open"].append(path)  # type: ignore

    # Click the Open button
    qtbot.mouseClick(win.btn_open, Qt.LeftButton)

    assert called["dlg"] is True
    assert called["open"] == []

