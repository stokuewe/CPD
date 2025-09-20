from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QDialog, QMessageBox
from src.services.recent_projects import RecentProjectsService
from src.services.logging_model import LoggingModel
from src.services.project_creator_local import ProjectCreatorLocal
from src.services.project_creator_remote import ProjectCreatorRemote
from src.services.app_context import app_context


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
        from PySide6.QtWidgets import QFileDialog, QMessageBox, QDialog, QPushButton
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
            # Create local project off the UI thread
            from src.services.background_runner import run_bg
            if hasattr(self.view, "start_busy"):
                self.view.start_busy()

            def work():
                self.create_project_local(fname)
                return True

            def on_ok(_):
                # Update recent and UI on the main thread
                self.recent_service.add(str(fname))
                self._log("INFO", f"Created local project: {fname}")
                if self.view is not None and hasattr(self.view, "show_recent"):
                    self.view.show_recent(self.recent_service.list())
                if hasattr(self.view, "stop_busy"):
                    self.view.stop_busy()
                # Auto-open the newly created project
                try:
                    self.open_project(fname)
                except Exception:
                    pass

            def on_err(exc: BaseException):
                QMessageBox.warning(self.view, "Create Project", str(exc))
                if hasattr(self.view, "stop_busy"):
                    self.view.stop_busy()

            run_bg(work, on_result=on_ok, on_error=on_err)
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

                # Run remote project creation off UI thread
                from src.services.background_runner import run_bg
                desc = dlg.descriptor()
                desc_with_password = dlg.descriptor_with_password()

                def work():
                    # 1) Validate remote connection descriptor (with password for testing)
                    self.create_project_remote(desc_with_password)
                    # 2) Initialize local settings DB for this project
                    self.create_project_local(fname)
                    # 3) Persist remote descriptor (excluding password) and mark storage_mode in settings
                    import sqlite3
                    with sqlite3.connect(fname) as conn:
                        conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('storage_mode', 'mssql')")
                        server = (desc.get('server') or '')
                        database = (desc.get('database') or '')
                        auth_type = (desc.get('auth_type') or 'windows').lower()
                        port = desc.get('port') if isinstance(desc.get('port'), int) else 1433
                        username = desc.get('username') or ''
                        authority = desc.get('authority') or ''
                        use_driver17 = 1 if desc.get('use_driver17') else 0
                        kvs = [
                            ('remote_server', server),
                            ('remote_database', database),
                            ('remote_port', str(port)),
                            ('remote_auth_type', auth_type),
                            ('remote_username', username),
                            ('remote_authority', authority),
                            ('remote_use_driver17', str(use_driver17)),
                        ]
                        for k, v in kvs:
                            conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (k, v))
                        if auth_type in ('sql', 'windows'):
                            uname_for_row = username if auth_type == 'sql' else None
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO mssql_connection
                                  (id, server, database, port, auth_type, username, password)
                                VALUES (1, ?, ?, ?, ?, ?, NULL)
                                """,
                                (server, database, port, auth_type, uname_for_row),
                            )
                        conn.commit()
                    return True

                def on_ok(_):
                    self.recent_service.add(str(fname))
                    self._log("INFO", f"Created remote project settings at: {fname}")
                    if self.view is not None and hasattr(self.view, "show_recent"):
                        self.view.show_recent(self.recent_service.list())
                    if hasattr(self.view, "stop_busy"):
                        self.view.stop_busy()
                    # Auto-open the newly created project
                    try:
                        self.open_project(fname)
                    except Exception:
                        pass

                def on_err(exc: BaseException):
                    try:
                        exc_str = str(exc)

                        # Handle schema validation errors during project creation
                        if exc_str in ("SCHEMA_DEPLOYMENT_REQUIRED", "SCHEMA_DEVIATIONS_DETECTED"):
                            self._handle_schema_validation_error(Path(fname), exc_str)
                            return

                        # Truncate very long error messages for display
                        display_msg = exc_str
                        if len(display_msg) > 500:
                            display_msg = display_msg[:500] + "..."

                        # Log the full error for debugging
                        self._log("ERROR", f"Create Remote Project failed: {exc_str}")

                        QMessageBox.warning(self.view, "Create Remote Project", display_msg)
                        if hasattr(self.view, "stop_busy"):
                            self.view.stop_busy()
                    except Exception as callback_exc:
                        # If the error callback itself fails, log it and try to recover
                        self._log("ERROR", f"Error callback failed: {callback_exc}")
                        try:
                            QMessageBox.warning(self.view, "Create Remote Project", "An error occurred during project creation.")
                            if hasattr(self.view, "stop_busy"):
                                self.view.stop_busy()
                        except Exception:
                            # Last resort - just log
                            self._log("ERROR", "Failed to show error dialog")

                run_bg(work, on_result=on_ok, on_error=on_err)
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

    def on_settings_clicked(self) -> None:  # pragma: no cover - UI wiring stub
        from PySide6.QtWidgets import QMessageBox
        from src.app.dialogs.settings_dialog import SettingsDialog
        # Require a loaded project to edit project settings
        if not app_context.project:
            if self.view is not None:
                QMessageBox.information(self.view, "Settings", "Open a project first to edit settings.")
            return
        dlg = SettingsDialog(self.view)
        if dlg.exec() == QMessageBox.Accepted:
            try:
                dlg.save_state()
            except Exception as exc:
                if self.view is not None:
                    QMessageBox.warning(self.view, "Settings", f"Failed to save settings: {exc}")
                return
            # Apply DB logging toggle immediately
            gw = app_context.gateway
            if gw is not None:
                enabled_val = app_context.get_setting("ui_db_logging", "1")
                enabled = str(enabled_val).strip().lower() in {"1", "true", "on", "yes"}
                if enabled:
                    def _db_observer(evt: dict) -> None:
                        op = evt.get("op", "?")
                        dur = evt.get("duration_ms", 0.0)
                        ok = bool(evt.get("success", False))
                        if ok:
                            rows = evt.get("rows") or evt.get("rowcount")
                            extra = f", rows={rows}" if rows is not None else ""
                            self._log("INFO", f"DB[{op}] OK in {dur:.1f} ms{extra}")
                        else:
                            cls = evt.get("error_class", "Error")
                            msg = evt.get("error_message", "")
                            self._log("ERROR", f"DB[{op}] FAIL in {dur:.1f} ms [{cls}] {msg}")
                    gw.set_observer(_db_observer)
                else:
                    gw.set_observer(None)

    def on_close_project_clicked(self) -> None:
        """Close the currently open project and return to startup screen"""
        from PySide6.QtWidgets import QMessageBox

        # Check if there's actually a project open
        if not app_context.project:
            if self.view is not None:
                QMessageBox.information(
                    self.view,
                    "Close Project",
                    "No project is currently open."
                )
            return

        # Confirm with user
        reply = QMessageBox.question(
            self.view,
            "Close Project",
            f"Close the current project?\n\nProject: {app_context.project.sqlite_path.name}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # Close the project (this clears credentials, closes gateway, etc.)
            app_context.close()

            # Update UI to reflect no project is open
            if self.view and hasattr(self.view, "set_project_open_state"):
                self.view.set_project_open_state(False)

            # Log the action
            self._log("INFO", "Project closed successfully")

            # Show success message
            if self.view is not None:
                QMessageBox.information(
                    self.view,
                    "Close Project",
                    "Project closed successfully."
                )

        except Exception as exc:
            self._log("ERROR", f"Failed to close project: {exc}")
            if self.view is not None:
                QMessageBox.warning(
                    self.view,
                    "Close Project",
                    f"Failed to close project:\n\n{exc}"
                )

    # Flows ----------------------------------------------------------
    def open_project(self, project_path: str) -> None:
        from src.services.background_runner import run_bg
        from PySide6.QtWidgets import QMessageBox

        p = Path(project_path)
        if not p.exists():
            self._log("ERROR", f"Project not found: {p}")
            return

        # Prevent duplicate project loading
        if hasattr(self.view, "is_busy") and self.view.is_busy():
            self._log("WARNING", f"Project loading already in progress, ignoring duplicate request for: {p}")
            return

        # For remote projects, authenticate once in main thread
        storage_mode = self._read_storage_mode_from_project(p)
        if storage_mode == "mssql":
            if not self._authenticate_remote_project(p):
                return  # Authentication failed, don't proceed

        # Busy UI while loading
        if self.view is not None and hasattr(self.view, "start_busy"):
            self.view.start_busy()

        def work():
            # Perform blocking I/O off UI thread - authentication already completed in main thread
            try:
                app_context.load_project(str(p))
                mode = app_context.project.storage_mode if app_context.project else "unknown"
                return mode
            except Exception as e:
                raise

        def on_ok(mode: str) -> None:
            # Attach or remove DB observer based on project setting 'ui_db_logging'
            gw = app_context.gateway
            if gw is not None:
                enabled_val = app_context.get_setting("ui_db_logging", "1")
                enabled = str(enabled_val).strip().lower() in {"1", "true", "on", "yes"}
                if enabled:
                    def _db_observer(evt: dict) -> None:
                        op = evt.get("op", "?")
                        dur = evt.get("duration_ms", 0.0)
                        ok = bool(evt.get("success", False))
                        if ok:
                            rows = evt.get("rows") or evt.get("rowcount")
                            extra = f", rows={rows}" if rows is not None else ""
                            self._log("INFO", f"DB[{op}] OK in {dur:.1f} ms{extra}")
                        else:
                            cls = evt.get("error_class", "Error")
                            msg = evt.get("error_message", "")
                            self._log("ERROR", f"DB[{op}] FAIL in {dur:.1f} ms [{cls}] {msg}")
                    gw.set_observer(_db_observer)
                else:
                    gw.set_observer(None)

            self._log("INFO", f"Opened project: {p} (mode={mode})")
            self.recent_service.add(str(p))
            if self.view is not None and hasattr(self.view, "show_recent"):
                self.view.show_recent(self.recent_service.list())
            # Enable close project UI since project is now open
            if self.view is not None and hasattr(self.view, "set_project_open_state"):
                self.view.set_project_open_state(True)
            if self.view is not None and hasattr(self.view, "stop_busy"):
                self.view.stop_busy()

        def on_err(exc: BaseException) -> None:
            try:
                exc_str = str(exc)

                # Handle schema validation errors specially
                if exc_str in ("SCHEMA_DEPLOYMENT_REQUIRED", "SCHEMA_DEVIATIONS_DETECTED"):
                    self._handle_schema_validation_error(p, exc_str)
                    return

                self._log("ERROR", f"Failed to initialize project DB: {exc}")
                # Keep recent updated even if gateway init failed, so user can retry
                self.recent_service.add(str(p))
                if self.view is not None and hasattr(self.view, "show_recent"):
                    self.view.show_recent(self.recent_service.list())
                if self.view is not None:
                    try:
                        QMessageBox.warning(self.view, "Open Project", str(exc))
                    except Exception:
                        pass
                if self.view is not None and hasattr(self.view, "stop_busy"):
                    self.view.stop_busy()
            except Exception as e:
                import traceback
                traceback.print_exc()

        run_bg(work, on_result=on_ok, on_error=on_err)

    def _handle_schema_validation_error(self, project_path: Path, error_type: str) -> None:
        """Handle schema validation errors with user interaction"""
        from src.app.dialogs.schema_validation_dialog import SchemaValidationDialog, SchemaDeploymentProgressDialog
        from src.services.background_runner import run_bg

        # Get pending validation data
        validation_data = app_context.get_pending_schema_validation()
        if not validation_data:
            self._log("ERROR", "Schema validation error but no pending data")
            if self.view is not None and hasattr(self.view, "stop_busy"):
                self.view.stop_busy()
            return

        result = validation_data['result']
        project_name = project_path.stem

        # Show schema validation dialog
        dialog = SchemaValidationDialog(self.view, result, project_name)

        if self.view is not None and hasattr(self.view, "stop_busy"):
            self.view.stop_busy()

        if dialog.exec() == QDialog.Accepted:
            choice = dialog.user_choice

            if choice == 'deploy':
                self._deploy_schema_and_continue(project_path)
                return  # Don't clear validation data yet - deployment needs it
            elif choice == 'proceed':
                self._proceed_with_project_loading(project_path)
            # 'cancel' - do nothing, project loading is cancelled

        # Clear pending validation data (only if not deploying)
        app_context.clear_pending_schema_validation()

    def _deploy_schema_and_continue(self, project_path: Path) -> None:
        """Deploy schema and continue with project loading"""
        from src.app.dialogs.schema_validation_dialog import SchemaDeploymentProgressDialog
        from src.services.background_runner import run_bg

        # Show progress dialog
        progress_dialog = SchemaDeploymentProgressDialog(self.view)
        progress_dialog.show()

        def deploy_work():
            progress_dialog.update_status("Deploying schema...")
            app_context.handle_schema_deployment()
            progress_dialog.update_status("Schema deployment completed...")
            # No need to reload project - schema deployment just added tables to existing connection
            return app_context.project.storage_mode if app_context.project else "unknown"

        def deploy_success(mode: str):
            progress_dialog.close()
            # Clear pending validation data after successful deployment
            app_context.clear_pending_schema_validation()
            self._log("INFO", f"Schema deployed successfully for project: {project_path}")
            self._log("INFO", f"Opened project: {project_path} (mode={mode})")
            self.recent_service.add(str(project_path))
            if self.view is not None and hasattr(self.view, "show_recent"):
                self.view.show_recent(self.recent_service.list())

        def deploy_error(exc: BaseException):
            progress_dialog.close()
            # Clear pending validation data after deployment failure
            app_context.clear_pending_schema_validation()
            self._log("ERROR", f"Schema deployment failed: {exc}")
            QMessageBox.critical(self.view, "Schema Deployment Failed",
                               f"Failed to deploy database schema:\n\n{exc}")

        run_bg(deploy_work, on_result=deploy_success, on_error=deploy_error)

    def _proceed_with_project_loading(self, project_path: Path) -> None:
        """Proceed with project loading despite schema issues"""
        from src.services.background_runner import run_bg

        if self.view is not None and hasattr(self.view, "start_busy"):
            self.view.start_busy()

        def work():
            # Force load project bypassing schema validation
            app_context._pending_schema_validation = None  # Clear to avoid re-validation
            app_context.load_project(str(project_path))
            return app_context.project.storage_mode if app_context.project else "unknown"

        def on_ok(mode: str):
            self._log("WARNING", f"Opened project with schema deviations: {project_path} (mode={mode})")
            self.recent_service.add(str(project_path))
            if self.view is not None and hasattr(self.view, "show_recent"):
                self.view.show_recent(self.recent_service.list())
            # Enable close project UI since project is now open
            if self.view is not None and hasattr(self.view, "set_project_open_state"):
                self.view.set_project_open_state(True)
            if self.view is not None and hasattr(self.view, "stop_busy"):
                self.view.stop_busy()

        def on_err(exc: BaseException):
            self._log("ERROR", f"Failed to open project: {exc}")
            QMessageBox.warning(self.view, "Open Project", str(exc))
            if self.view is not None and hasattr(self.view, "stop_busy"):
                self.view.stop_busy()

        run_bg(work, on_result=on_ok, on_error=on_err)

    def create_project_local(self, target_path: str) -> None:
        # Pure creation operation; no UI or logging from background threads
        creator = ProjectCreatorLocal(target_path)
        creator.create()
        # Caller is responsible for logging, recent updates, and UI refresh on the UI thread

    def create_project_remote(self, descriptor: dict) -> None:
        # Pure validation of remote descriptor; no UI or logging here
        creator = ProjectCreatorRemote(descriptor)
        creator.create()
        # Caller handles any subsequent UI/logging

    # Helper methods for connection testing -------------------------
    def _read_storage_mode_from_project(self, project_path: Path) -> str:
        """Read storage mode from project file without loading the full project"""
        import sqlite3
        try:
            with sqlite3.connect(str(project_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = 'storage_mode'")
                row = cursor.fetchone()
                return row[0] if row else "sqlite"
        except Exception:
            return "sqlite"  # Default fallback

    def _authenticate_remote_project(self, project_path: Path) -> bool:
        """Authenticate remote database connection once and cache token (main thread only)"""
        from PySide6.QtWidgets import QMessageBox
        from src.services.azure_ad_token_manager import get_token_manager, ConnectionDescriptor
        import sqlite3

        # Store project path for credential management
        self._current_project_path = project_path

        try:
            # Read connection details from project file
            with sqlite3.connect(str(project_path)) as conn:
                cursor = conn.cursor()

                settings_keys = [
                    'remote_server', 'remote_database', 'remote_auth_type',
                    'remote_username', 'remote_authority', 'remote_port'
                ]

                cursor.execute("""
                    SELECT key, value FROM settings
                    WHERE key IN ({})
                """.format(','.join('?' * len(settings_keys))), settings_keys)

                settings = dict(cursor.fetchall())

                server = settings.get('remote_server')
                database = settings.get('remote_database')
                auth_type = settings.get('remote_auth_type')
                username = settings.get('remote_username')
                authority = settings.get('remote_authority')
                port = settings.get('remote_port')

                if not server or not database or not auth_type:
                    raise ValueError("Incomplete MSSQL connection configuration")

                # Add port to server if provided (same logic as app_context._read_remote_descriptor)
                if server and "," not in server and port and port.isdigit():
                    server = f"{server},{port}"

                # Create connection descriptor
                descriptor = ConnectionDescriptor(
                    server=server,
                    database=database,
                    auth_type=auth_type,
                    username=username,
                    authority=authority,
                    timeout_seconds=30
                )

                # Handle authentication based on auth type
                if auth_type.lower() == "sql":
                    # For SQL authentication, prompt for password since it's not stored
                    return self._authenticate_sql_project(descriptor)
                else:
                    # For Azure AD authentication, use token manager
                    token_manager = get_token_manager()
                    success = token_manager.authenticate_and_cache(descriptor)

                    if not success:
                        QMessageBox.critical(
                            self.view,
                            "Authentication Failed",
                            f"Cannot authenticate to remote database.\n\n"
                            f"Server: {server}\n"
                            f"Database: {database}\n"
                            f"Auth Type: {auth_type}\n\n"
                            f"Please check your credentials and try again."
                        )
                        return False

                    return True

        except Exception as e:
            QMessageBox.critical(
                self.view,
                "Project Opening Failed",
                f"Cannot read project configuration:\n\n{e}\n\nPlease check the project file."
            )
            return False

    def _authenticate_sql_project(self, descriptor) -> bool:
        """Authenticate SQL Server project by prompting for password"""
        from src.app.dialogs.mssql_connection_dialog import MSSQLConnectionDialog
        from PySide6.QtWidgets import QMessageBox

        # Create dialog with pre-filled connection details
        dialog = MSSQLConnectionDialog(self.view)
        dialog.setWindowTitle("Enter Database Password")

        # Pre-fill the dialog with stored connection details
        dialog.server.setText(descriptor.server or "")
        dialog.database.setText(descriptor.database or "")

        # Map internal auth_type to display name
        auth_type_display_mapping = {
            "sql": "MS-SQL",
            "azure_ad_interactive": "Azure AD Interactive",
            "azure_ad_integrated": "Azure AD Integrated"
        }
        internal_auth_type = descriptor.auth_type or "sql"
        display_auth_type = auth_type_display_mapping.get(internal_auth_type, "MS-SQL")
        dialog.auth_type.setCurrentText(display_auth_type)

        dialog.username.setText(descriptor.username or "")

        # Focus on password field
        dialog.password.setFocus()

        # Show dialog and wait for user input
        from PySide6.QtWidgets import QDialog
        if dialog.exec() == QDialog.Accepted:
            # Test connection was successful, store password securely for project session
            password = dialog.password.text()
            if password:
                # Store password securely in credential manager
                from src.services.secure_credential_manager import get_credential_manager
                credential_manager = get_credential_manager()
                project_key = str(self._current_project_path)
                credential_manager.store_password(project_key, password)
            return True
        else:
            # User cancelled or connection failed
            return False

    def _perform_connection_test(self, descriptor: dict) -> bool:
        """Perform actual connection test in main thread using token manager"""
        from PySide6.QtWidgets import QMessageBox
        from src.services.azure_ad_token_manager import get_token_manager, ConnectionDescriptor

        try:
            # Create connection descriptor for token manager
            conn_descriptor = ConnectionDescriptor(
                server=descriptor.get("server", ""),
                database=descriptor.get("database", ""),
                auth_type=descriptor.get("auth_type", "windows"),
                username=descriptor.get("username"),
                authority=descriptor.get("authority"),
                timeout_seconds=descriptor.get("connect_timeout_seconds", 30)
            )

            # Use token manager for Azure AD authentication
            if conn_descriptor.auth_type.startswith("azure_ad"):
                token_manager = get_token_manager()
                conn_str = token_manager.get_connection_string(conn_descriptor)

                # Test the connection
                import pyodbc
                with pyodbc.connect(conn_str, autocommit=True, timeout=conn_descriptor.timeout_seconds):
                    pass

                return True  # Connection successful and token cached
            else:
                # Non-Azure AD authentication - use traditional method
                from src.services.mssql_connection import build_connect_kwargs
                kwargs = build_connect_kwargs(descriptor)
                if not kwargs.get("Server") or not kwargs.get("Database"):
                    raise ValueError("Server and Database are required")

                conn_str = self._build_connection_string_for_test(descriptor)
                import pyodbc
                timeout_sec = kwargs.get("Timeout", 30)
                with pyodbc.connect(conn_str, autocommit=True, timeout=timeout_sec):
                    pass

                return True  # Connection successful

        except Exception as e:
            # Handle Azure AD Interactive 0x534 error with fallback to Driver 17
            if "0x534" in str(e) and descriptor.get("auth_type") == "azure_ad_interactive":
                try:
                    conn_str_17 = self._build_connection_string_for_test_driver17(descriptor)
                    import pyodbc
                    with pyodbc.connect(conn_str_17, autocommit=True, timeout=descriptor.get("connect_timeout_seconds", 30)):
                        pass

                    # Cache the successful authentication with Driver 17
                    # Update the connection string building to use Driver 17 for this descriptor
                    return True  # Connection successful with Driver 17
                except Exception as e2:
                    e = e2  # Use the Driver 17 error for display

            QMessageBox.critical(
                self.view,
                "Connection Test Failed",
                f"Cannot connect to remote database:\n\n{e}\n\nPlease check your connection settings and try again."
            )
            return False

    def _build_connection_string_for_test(self, descriptor: dict) -> str:
        """Build ODBC connection string for testing (same as MSSQLConnectionDialog)"""
        parts = ["DRIVER={ODBC Driver 18 for SQL Server}"]

        if descriptor.get("server"):
            parts.append(f"SERVER={descriptor['server']}")
        if descriptor.get("database"):
            parts.append(f"DATABASE={descriptor['database']}")

        auth_type = (descriptor.get("auth_type") or "").lower()
        if auth_type == "windows":
            parts.append("Trusted_Connection=yes")
        elif auth_type == "sql":
            if descriptor.get("username"):
                parts.append(f"UID={descriptor['username']}")
        elif auth_type == "azure_ad_interactive":
            parts.append("Authentication=ActiveDirectoryInteractive")
            if descriptor.get("username"):
                parts.append(f"UID={descriptor['username']}")
        elif auth_type == "azure_ad_password":
            parts.append("Authentication=ActiveDirectoryPassword")
            if descriptor.get("username"):
                parts.append(f"UID={descriptor['username']}")
        elif auth_type == "azure_ad_integrated":
            parts.append("Authentication=ActiveDirectoryIntegrated")
        elif auth_type == "azure_ad_device_code":
            parts.append("Authentication=ActiveDirectoryDeviceCode")
            if descriptor.get("username"):
                parts.append(f"UID={descriptor['username']}")
        else:
            parts.append("Trusted_Connection=yes")

        if auth_type.startswith("azure_ad") and descriptor.get("authority"):
            parts.append(f"Authority={descriptor['authority']}")

        parts.append("Encrypt=yes")
        if auth_type.startswith("azure_ad"):
            parts.append("TrustServerCertificate=yes")
        else:
            parts.append("TrustServerCertificate=no")

        return ";".join(parts)

    def _build_connection_string_for_test_driver17(self, descriptor: dict) -> str:
        """Build ODBC connection string using Driver 17 for fallback"""
        conn_str = self._build_connection_string_for_test(descriptor)
        return conn_str.replace("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server")

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

