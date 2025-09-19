from __future__ import annotations

import pytest

from src.app.main_window import MainWindow


@pytest.mark.qt_no_exception_capture
def test_progress_dialog_shows_after_one_second(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()

    # Start busy operation
    win.start_busy()

    # Before 1s: dialog should not be visible
    qtbot.wait(300)
    assert win.progress_dialog is None or not win.progress_dialog.isVisible()

    # After >= 1s: dialog should be visible
    qtbot.wait(1100)
    assert win.progress_dialog is not None and win.progress_dialog.isVisible()

    # Stop busy should hide dialog
    win.stop_busy()
    qtbot.wait(50)
    assert win.progress_dialog is None or not win.progress_dialog.isVisible()

