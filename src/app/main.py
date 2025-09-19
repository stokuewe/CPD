from __future__ import annotations

import logging
import sys
import weakref
from pathlib import Path

from PySide6 import QtWidgets

from src.logging.config import configure_logging
from src.logging.gui_bridge import build_gui_handler
from src.services.migration_service import MigrationService
from src.services.project_service import ProjectService, ProjectState
from src.storage.sqlite_adapter import SQLiteAdapter
from src.ui import message_dialogs
from src.ui.startup_window import StartupWindow

RECENT_PROJECTS_FILE = Path.home() / ".cpd" / "recent_projects.json"


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)

    RECENT_PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    window_ref: weakref.ReferenceType[StartupWindow] | None = None

    def backup_warning(path: Path, current: str, target: str) -> None:
        window = window_ref() if window_ref else None
        parent = window if window is not None else QtWidgets.QApplication.activeWindow()
        message_dialogs.show_backup_warning(parent, path, current, target)

    project_service = ProjectService(
        sqlite_adapter_factory=SQLiteAdapter,
        migration_service_factory=MigrationService,
        recent_projects_path=RECENT_PROJECTS_FILE,
        backup_warning=backup_warning,
    )

    window = StartupWindow(project_service, recent_projects_path=RECENT_PROJECTS_FILE)
    window_ref = weakref.ref(window)

    configure_logging(lambda: build_gui_handler(window.log_sink))

    def on_project_loaded(state: ProjectState) -> None:
        logging.getLogger(__name__).info(
            "Project ready",
            extra={
                "path": str(state.settings_path),
                "mode": state.storage_mode,
                "read_only": state.read_only,
            },
        )
        if state.read_only:
            message_dialogs.show_warning(
                window,
                "Read-Only Mode",
                "Remote database is unreachable. Project opened in read-only mode.",
            )

    window.project_loaded.connect(on_project_loaded)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
