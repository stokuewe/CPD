from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.services.recent_projects import RecentProjectsService
from src.services.logging_model import LoggingModel
from src.services.project_creator_local import ProjectCreatorLocal
from src.services.project_creator_remote import ProjectCreatorRemote


class StartupController:
    """Wires Startup view actions to services (M1 skeleton + basic flows).

    Provides methods for open/create flows used by integration tasks.
    """

    def __init__(
        self,
        recent_service: Optional[RecentProjectsService] = None,
        logger: Optional[LoggingModel] = None,
    ) -> None:
        self.recent_service = recent_service or RecentProjectsService()
        self.logger = logger or LoggingModel()
        self.view = None

    # Utility --------------------------------------------------------
    def _log(self, level: str, message: str) -> None:
        self.logger.log(level, message)
        if self.view is not None and hasattr(self.view, "append_log"):
            self.view.append_log(level, message)

    # Slots for MainWindow wiring -----------------------------------
    def on_open_clicked(self) -> None:  # pragma: no cover - UI wiring stub
        from PySide6.QtWidgets import QFileDialog

        self._log("INFO", "Open Project clicked")
        if self.view is None:
            return
        # Only open selected recent if the user explicitly selected something
        lst = getattr(self.view, "recent_list", None)
        try:
            if lst is not None and lst.selectionModel() and lst.selectionModel().hasSelection():
                sel = lst.currentItem()
                if sel is not None:
                    path = getattr(sel, "text", lambda: "")()
                    if path:
                        self.open_project(path)
                        return
        except Exception:
            # Fallback to dialog on any issue
            pass
        # Otherwise ask via file dialog
        fname, _ = QFileDialog.getOpenFileName(
            self.view,
            "Open Project",
            filter="SQLite Project (*.sqlite);;All Files (*.*)",
        )
        if not fname:
            return
        self.open_project(fname)

    def on_create_clicked(self) -> None:  # pragma: no cover - UI wiring stub
        from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton
        from src.app.dialogs.mssql_connection_dialog import MSSQLConnectionDialog

        self._log("INFO", "Create Project clicked")
        if self.view is None:
            return

        # Ask user: Local or Remote
        box = QMessageBox(self.view)
        box.setWindowTitle("Create Project")
        box.setText("Choose storage mode for the new project:")
        btn_local = box.addButton("Local (SQLite)...", QMessageBox.AcceptRole)
        btn_remote = box.addButton("Remote (MSSQL)...", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Cancel)
        box.exec()
        clicked = box.clickedButton()

        if clicked is btn_local:
            fname, _ = QFileDialog.getSaveFileName(
                self.view,
                "Create Local Project",
                filter="SQLite Project (*.sqlite)",
            )
            if not fname:
                return
            if not fname.lower().endswith(".sqlite"):
                fname = f"{fname}.sqlite"
            # Create local project
            if hasattr(self.view, "start_busy"):
                self.view.start_busy()
            try:
                self.create_project_local(fname)
            except Exception as exc:  # show error
                QMessageBox.warning(self.view, "Create Project", str(exc))
            finally:
                if hasattr(self.view, "stop_busy"):
                    self.view.stop_busy()
            return

        if clicked is btn_remote:
            # Choose local SQLite settings file for the project (always required)
            fname, _ = QFileDialog.getSaveFileName(
                self.view,
                "Create Remote Project - Choose Settings File",
                filter="SQLite Project (*.sqlite)",
            )
            if not fname:
                return
            if not fname.lower().endswith(".sqlite"):
                fname = f"{fname}.sqlite"

            dlg = MSSQLConnectionDialog(self.view)
            if dlg.exec() == QMessageBox.Accepted:
                if hasattr(self.view, "start_busy"):
                    self.view.start_busy()
                try:
                    # 1) Validate remote connection descriptor (and require successful Test via gating)
                    desc = dlg.descriptor()
                    self.create_project_remote(desc)
                    # 2) Initialize local settings DB for this project
                    self.create_project_local(fname)
                    # 3) Persist remote descriptor (excluding password) and mark storage_mode in settings
                    try:
                        import sqlite3
                        with sqlite3.connect(fname) as conn:
                            conn.execute(
                                "INSERT OR REPLACE INTO settings(key, value) VALUES('storage_mode', 'mssql')"
                            )
                            # mssql_connection singleton row (id=1)
                            server = desc.get("server", "")
                            database = desc.get("database", "")
                            auth_type = (desc.get("auth_type") or "windows").lower()
                            port = desc.get("port") if isinstance(desc.get("port"), int) else 1433
                            username = desc.get("username") if auth_type == "sql" else None
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO mssql_connection
                                  (id, server, database, port, auth_type, username, password)
                                VALUES (1, ?, ?, ?, ?, ?, NULL)
                                """,
                                (server, database, port, auth_type, username),
                            )
                            conn.commit()
                    except Exception as persist_exc:
                        # Show a warning but keep the project file created; user can retry settings save
                        QMessageBox.warning(self.view, "Create Remote Project", f"Project created, but failed to save connection details: {persist_exc}")

                    # Add to recent and refresh
                    self.recent_service.add(str(fname))
                    self._log("INFO", f"Created remote project settings at: {fname}")
                    if self.view is not None:
                        self.view.show_recent(self.recent_service.list())
                except Exception as exc:
                    QMessageBox.warning(self.view, "Create Remote Project", str(exc))
                finally:
                    if hasattr(self.view, "stop_busy"):
                        self.view.stop_busy()
            return

    def on_clear_recent_clicked(self) -> None:  # pragma: no cover - UI wiring stub
        self.recent_service.clear()
        self._log("INFO", "Recent projects cleared")
        if self.view is not None:
            self.view.show_recent(self.recent_service.list())

    def on_recent_activated(self, path: str) -> None:  # pragma: no cover - UI wiring stub
        if path:
            self.open_project(path)

    def on_recent_remove(self, path: str) -> None:  # pragma: no cover - UI wiring stub
        if not path:
            return
        self.recent_service.remove(path)
        self._log("INFO", f"Removed from recent: {path}")
        if self.view is not None:
            self.view.show_recent(self.recent_service.list())

    # Flows ----------------------------------------------------------
    def open_project(self, project_path: str) -> None:
        p = Path(project_path)
        if not p.exists():
            self._log("ERROR", f"Project not found: {p}")
            return
        # Future: invoke ProjectLoader and migration handling
        self.recent_service.add(str(p))
        self._log("INFO", f"Opened project: {p}")
        if self.view is not None:
            self.view.show_recent(self.recent_service.list())

    def create_project_local(self, target_path: str) -> None:
        creator = ProjectCreatorLocal(target_path)
        creator.create()
        self.recent_service.add(str(target_path))
        self._log("INFO", f"Created local project: {target_path}")
        if self.view is not None:
            self.view.show_recent(self.recent_service.list())

    def create_project_remote(self, descriptor: dict) -> None:
        creator = ProjectCreatorRemote(descriptor)
        creator.create()
        self._log("INFO", "Configured remote project (descriptor stored locally without password)")
        if self.view is not None:
            self.view.show_recent(self.recent_service.list())

    # View attachment ------------------------------------------------
    def attach_view(self, view) -> None:  # pragma: no cover - UI wiring stub
        self.view = view
        if hasattr(view, "set_controller"):
            view.set_controller(self)
        if hasattr(view, "show_recent"):
            view.show_recent(self.recent_service.list())
        # Replay existing logs to the view
        if hasattr(self.logger, "entries") and hasattr(view, "append_log"):
            for e in self.logger.entries():
                view.append_log(e.level, e.message)

