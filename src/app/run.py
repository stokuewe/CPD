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

    try:
        return app.exec()
    finally:
        # Cleanup secure credentials on application exit
        try:
            from src.services.secure_credential_manager import cleanup_credentials
            cleanup_credentials()
        except Exception:
            pass  # Ignore cleanup errors


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

