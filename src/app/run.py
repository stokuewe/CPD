from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from src.app.main_window import MainWindow
from src.app.controllers.startup_controller import StartupController


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    controller = StartupController()
    win = MainWindow()
    controller.attach_view(win)

    win.resize(900, 600)
    win.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

