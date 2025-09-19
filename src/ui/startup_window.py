from __future__ import annotations

import logging
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from src.core.errors import UserFacingError
from src.services.project_service import ProjectService, ProjectState
from src.services.recent_projects import RecentProjectEntry, load_once, save
from src.ui import message_dialogs
from src.ui.create_project_dialog import CreateProjectDialog
from src.ui.log_panel import LogPanel


class StartupWindow(QtWidgets.QMainWindow):
    project_loaded = QtCore.Signal(ProjectState)

    def __init__(
        self,
        project_service: ProjectService,
        *,
        recent_projects_path: Path,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("CPD - Common Project Database")
        self.resize(900, 600)

        self._project_service = project_service
        self._recent_projects_path = recent_projects_path
        self._logger = logging.getLogger(__name__)

        self._recent_list = QtWidgets.QListWidget()
        self._recent_list.itemDoubleClicked.connect(self._open_selected_recent)

        open_button = QtWidgets.QPushButton("Open")
        open_button.clicked.connect(lambda: self._open_selected_recent())

        open_other_button = QtWidgets.QPushButton("Open...")
        open_other_button.clicked.connect(self._open_via_dialog)

        create_button = QtWidgets.QPushButton("Create...")
        create_button.clicked.connect(self._create_project)

        clear_button = QtWidgets.QPushButton("Clear Recent List")
        clear_button.clicked.connect(self._clear_recent_list)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(open_button)
        buttons_layout.addWidget(open_other_button)
        buttons_layout.addWidget(create_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(clear_button)

        recent_group = QtWidgets.QGroupBox("Recent Projects")
        recent_layout = QtWidgets.QVBoxLayout()
        recent_layout.addWidget(self._recent_list)
        recent_layout.addLayout(buttons_layout)
        recent_group.setLayout(recent_layout)

        self._log_panel = LogPanel()

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Vertical)
        splitter.addWidget(recent_group)
        splitter.addWidget(self._log_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

        self._readonly_indicator = QtWidgets.QLabel("")
        self.statusBar().addPermanentWidget(self._readonly_indicator)

        self._reload_recent_list()

    @property
    def log_sink(self):
        return self._log_panel.append_record

    def _reload_recent_list(self) -> None:
        self._recent_list.clear()
        entries = load_once(self._recent_projects_path)
        for entry in entries:
            item = QtWidgets.QListWidgetItem(str(entry.path))
            item.setData(QtCore.Qt.UserRole, entry)
            self._recent_list.addItem(item)

    def _open_selected_recent(self, item: QtWidgets.QListWidgetItem | None = None) -> None:
        if item is None:
            item = self._recent_list.currentItem()
        if item is None:
            self._open_via_dialog()
            return
        entry: RecentProjectEntry = item.data(QtCore.Qt.UserRole)
        self._open_project(entry.path)

    def _open_via_dialog(self) -> None:
        path_str, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Project", str(Path.home()), "SQLite DB (*.sqlite);;All Files (*.*)"
        )
        if path_str:
            self._open_project(Path(path_str))

    def _open_project(self, path: Path) -> None:
        try:
            state = self._project_service.open_project(path)
        except UserFacingError as exc:  # pragma: no cover - user feedback path
            message_dialogs.show_user_error(self, exc)
            return
        except Exception as exc:  # pragma: no cover - user feedback path
            self._logger.exception("Failed to open project")
            message_dialogs.show_error(self, "Open Failed", str(exc))
            return

        self._after_project_loaded(state, f"Opened project at {path}")

    def _create_project(self) -> None:
        dialog = CreateProjectDialog(self._project_service.test_mssql_connection, parent=self)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        path = dialog.selected_path()
        mode = dialog.storage_mode()
        params = dialog.mssql_params()

        try:
            state = self._project_service.create_project(path, storage_mode=mode, mssql_profile=params)
        except UserFacingError as exc:  # pragma: no cover - user feedback path
            message_dialogs.show_user_error(self, exc)
            return
        except Exception as exc:  # pragma: no cover - user feedback path
            self._logger.exception("Failed to create project")
            message_dialogs.show_error(self, "Create Failed", str(exc))
            return

        self._after_project_loaded(state, f"Created project at {path}")

    def _clear_recent_list(self) -> None:
        confirm = message_dialogs.ask_confirmation(
            self,
            "Clear Recent Projects",
            "This will clear all recent project entries. Continue?",
        )
        if not confirm:
            return
        save(self._recent_projects_path, [])
        self._reload_recent_list()
        self.statusBar().showMessage("Recent projects cleared", 5000)
        self._logger.info("Recent projects cleared", extra={"operation": "clear_recent"})

    def _after_project_loaded(self, state: ProjectState, status_message: str) -> None:
        self._reload_recent_list()
        indicator = "READ-ONLY" if state.read_only else ""
        self._readonly_indicator.setText(indicator)
        if state.read_only:
            self.statusBar().showMessage(
                f"{status_message} (remote database unavailable - read-only mode)", 7000
            )
        else:
            self.statusBar().showMessage(status_message, 5000)
        self.project_loaded.emit(state)


__all__ = ["StartupWindow"]
