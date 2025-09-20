from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
)

from src.services.mssql_connection import build_connect_kwargs, map_exception


class MSSQLConnectionDialog(QDialog):
    """Dialog for entering MSSQL connection details.

    Includes a Test Connection button. Passwords are never persisted.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Remote Connection")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.server = QLineEdit()
        self.database = QLineEdit()
        self.port = QLineEdit()
        self.auth_type = QComboBox()
        # Simplified authentication options
        self.auth_type.addItems(["MS-SQL", "Azure AD Interactive", "Azure AD Integrated"])
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        form.addRow("Server", self.server)
        form.addRow("Database", self.database)
        form.addRow("Port", self.port)
        form.addRow("Auth Type", self.auth_type)
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.btn_test = QPushButton("Test Connection")
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")
        btn_row.addWidget(self.btn_test)
        btn_row.addWidget(self.btn_ok)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

        # Gate OK until a successful Test Connection
        self._test_ok = False
        self._use_driver17 = False  # Track if Driver 17 was successful
        self.btn_ok.setEnabled(False)

        # Wiring
        self.btn_test.clicked.connect(self.on_test)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.auth_type.currentTextChanged.connect(self._on_auth_type_changed)

        # Invalidate test when fields change
        for w in (self.server, self.database, self.port, self.username, self.password):
            w.textChanged.connect(self._invalidate_test)
        self.auth_type.currentTextChanged.connect(self._invalidate_test)

        # Initialize auth-dependent field state
        self._on_auth_type_changed(self.auth_type.currentText())

    def _invalidate_test(self, *args) -> None:
        self._test_ok = False
        self._use_driver17 = False  # Reset driver preference when settings change
        self.btn_ok.setEnabled(False)

    def _on_auth_type_changed(self, auth: str) -> None:
        # Handle display names from the combo box
        if auth == "MS-SQL":
            self.username.setEnabled(True)
            self.password.setEnabled(True)
        elif auth == "Azure AD Interactive":
            # Username optional (UPN hint), password not used
            self.username.setEnabled(True)
            self.password.setEnabled(False)
            self.password.clear()
        elif auth == "Azure AD Integrated":
            # Pure SSO; no explicit credentials
            self.username.setEnabled(False)
            self.password.setEnabled(False)
            self.username.clear()
            self.password.clear()
        else:
            # Default safe state
            self.username.setEnabled(False)
            self.password.setEnabled(False)
            self.password.clear()

    def descriptor(self) -> dict:
        # Map display names to internal auth_type values
        auth_type_mapping = {
            "MS-SQL": "sql",
            "Azure AD Interactive": "azure_ad_interactive",
            "Azure AD Integrated": "azure_ad_integrated"
        }

        display_auth_type = self.auth_type.currentText()
        internal_auth_type = auth_type_mapping.get(display_auth_type, "sql")

        d: dict = {
            "server": self.server.text().strip(),
            "database": self.database.text().strip(),
            "auth_type": internal_auth_type,
        }
        # Optional fields
        try:
            port_val = int(self.port.text()) if self.port.text().strip() else None
        except ValueError:
            port_val = None
        if port_val is not None:
            d["port"] = port_val

        # Username required for MS-SQL and Azure AD Interactive
        if internal_auth_type in ("sql", "azure_ad_interactive"):
            if self.username.text().strip():
                d["username"] = self.username.text().strip()
            # password intentionally not stored in descriptor
        return d

    def descriptor_with_password(self) -> dict:
        """Get descriptor including password for connection testing (never persisted)."""
        d = self.descriptor()
        # Add password only for connection testing - never stored
        if self.password.text():
            d["password"] = self.password.text()
        # Add driver preference if Driver 17 was successful
        if self._use_driver17:
            d["use_driver17"] = True
        return d

    def _build_odbc_connection_string(self) -> str:
        """Attempt to build a DSN-less ODBC connection string for pyodbc.
        Uses a common SQL Server ODBC driver name; may need adjustment per system.
        """
        desc = self.descriptor()
        kwargs = build_connect_kwargs(desc)
        parts = []
        # Prefer modern driver; fallback is environment-specific
        parts.append("DRIVER={ODBC Driver 18 for SQL Server}")
        if kwargs.get("Server"):
            parts.append(f"SERVER={kwargs['Server']}")
        if kwargs.get("Database"):
            parts.append(f"DATABASE={kwargs['Database']}")

        mode = (desc.get("auth_type") or "").lower()
        if mode == "windows" or kwargs.get("Trusted_Connection") == "yes":
            parts.append("Trusted_Connection=yes")
        elif mode == "sql":
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            pwd = self.password.text()
            if pwd:
                parts.append(f"PWD={pwd}")
        elif mode == "azure_ad_interactive":
            parts.append("Authentication=ActiveDirectoryInteractive")
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            # No password for interactive
        elif mode == "azure_ad_password":
            parts.append("Authentication=ActiveDirectoryPassword")
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            pwd = self.password.text()
            if pwd:
                parts.append(f"PWD={pwd}")
        elif mode == "azure_ad_integrated":
            parts.append("Authentication=ActiveDirectoryIntegrated")
            # No UID/PWD for integrated SSO
        elif mode == "azure_ad_device_code":
            parts.append("Authentication=ActiveDirectoryDeviceCode")
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            # No password for device code
        else:
            # Default to Windows safe behavior
            parts.append("Trusted_Connection=yes")

        # Optional Authority/Tenant for AAD modes
        if mode.startswith("azure_ad") and desc.get("authority"):
            parts.append(f"Authority={desc['authority']}")

        # Security defaults
        parts.append("Encrypt=yes")
        # For Azure AD authentication, trust server certificate to allow browser authentication
        if mode.startswith("azure_ad"):
            parts.append("TrustServerCertificate=yes")
        else:
            parts.append("TrustServerCertificate=no")
        # Do not include timeout in the connection string; pass via pyodbc.connect(..., timeout=...)
        return ";".join(parts)

    def _build_odbc_connection_string_for_desc(self, desc: dict) -> str:
        """Build ODBC connection string for a provided descriptor (no persistence)."""
        kwargs = build_connect_kwargs(desc)
        parts = []
        parts.append("DRIVER={ODBC Driver 18 for SQL Server}")
        if kwargs.get("Server"):
            parts.append(f"SERVER={kwargs['Server']}")
        if kwargs.get("Database"):
            parts.append(f"DATABASE={kwargs['Database']}")
        mode = (desc.get("auth_type") or "").lower()
        if mode == "windows" or kwargs.get("Trusted_Connection") == "yes":
            parts.append("Trusted_Connection=yes")
        elif mode == "sql":
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            pwd = self.password.text()
            if pwd:
                parts.append(f"PWD={pwd}")
        elif mode == "azure_ad_interactive":
            parts.append("Authentication=ActiveDirectoryInteractive")
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
        elif mode == "azure_ad_password":
            parts.append("Authentication=ActiveDirectoryPassword")
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            pwd = self.password.text()
            if pwd:
                parts.append(f"PWD={pwd}")
        elif mode == "azure_ad_integrated":
            parts.append("Authentication=ActiveDirectoryIntegrated")
        elif mode == "azure_ad_device_code":
            parts.append("Authentication=ActiveDirectoryDeviceCode")
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
        else:
            parts.append("Trusted_Connection=yes")
        # Optional Authority/Tenant for AAD modes
        if mode.startswith("azure_ad") and desc.get("authority"):
            parts.append(f"Authority={desc['authority']}")
        parts.append("Encrypt=yes")
        # For Azure AD authentication, trust server certificate to allow browser authentication
        if mode.startswith("azure_ad"):
            parts.append("TrustServerCertificate=yes")
        else:
            parts.append("TrustServerCertificate=no")
        return ";".join(parts)

    def _build_odbc_connection_string_for_desc_driver17(self, desc: dict) -> str:
        """Build ODBC connection string using Driver 17 for Azure AD compatibility."""
        kwargs = build_connect_kwargs(desc)
        parts = []
        parts.append("DRIVER={ODBC Driver 17 for SQL Server}")  # Use Driver 17 instead of 18
        if kwargs.get("Server"):
            parts.append(f"SERVER={kwargs['Server']}")
        if kwargs.get("Database"):
            parts.append(f"DATABASE={kwargs['Database']}")
        mode = (desc.get("auth_type") or "").lower()
        if mode == "windows" or kwargs.get("Trusted_Connection") == "yes":
            parts.append("Trusted_Connection=yes")
        elif mode == "sql":
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            pwd = self.password.text()
            if pwd:
                parts.append(f"PWD={pwd}")
        elif mode == "azure_ad_interactive":
            parts.append("Authentication=ActiveDirectoryInteractive")
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
        elif mode == "azure_ad_password":
            parts.append("Authentication=ActiveDirectoryPassword")
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            pwd = self.password.text()
            if pwd:
                parts.append(f"PWD={pwd}")
        elif mode == "azure_ad_integrated":
            parts.append("Authentication=ActiveDirectoryIntegrated")
        elif mode == "azure_ad_device_code":
            parts.append("Authentication=ActiveDirectoryDeviceCode")
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
        else:
            parts.append("Trusted_Connection=yes")
        # Optional Authority/Tenant for AAD modes
        if mode.startswith("azure_ad") and desc.get("authority"):
            parts.append(f"Authority={desc['authority']}")
        parts.append("Encrypt=yes")
        # For Azure AD authentication, trust server certificate to allow browser authentication
        if mode.startswith("azure_ad"):
            parts.append("TrustServerCertificate=yes")
        else:
            parts.append("TrustServerCertificate=no")
        return ";".join(parts)

    def on_test(self) -> None:  # pragma: no cover - UI interaction
        # First, validate inputs/map to kwargs
        try:
            desc = self.descriptor()
            kwargs = build_connect_kwargs(desc)
            if not kwargs.get("Server") or not kwargs.get("Database"):
                raise ValueError("Server and Database are required")
            mode = (desc.get("auth_type") or "").lower()
            if mode == "sql":
                if not desc.get("username") or not self.password.text():
                    raise ValueError("Username and Password are required for MS-SQL authentication")
            elif mode == "azure_ad_interactive":
                if not desc.get("username"):
                    raise ValueError("Username is required for Azure AD Interactive authentication")
        except Exception as exc:  # show actionable message with details
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Test Connection")
            box.setText(map_exception(exc))
            # Show exact driver error in Details to aid debugging (may include server/DB names, but not passwords)
            detail = str(exc) or repr(exc)
            if detail:
                box.setInformativeText("Driver error details are available below.")
                box.setDetailedText(detail)
            box.exec()
            return

        # Run connection test in background thread to prevent UI freezing
        self._run_connection_test_async(desc, kwargs)

    def _run_connection_test_async(self, desc: dict, kwargs: dict) -> None:
        """Run connection test in background thread to prevent UI freezing"""
        from src.services.background_runner import run_bg

        # Disable test button during test
        self.btn_test.setEnabled(False)
        self.btn_test.setText("Testing...")

        def test_work():
            return self._perform_connection_test(desc, kwargs)

        def on_success(result):
            self.btn_test.setEnabled(True)
            self.btn_test.setText("Test Connection")
            QMessageBox.information(self, "Test Connection", result)
            # Gate passed
            self._test_ok = True
            self.btn_ok.setEnabled(True)

        def on_error(exc):
            self.btn_test.setEnabled(True)
            self.btn_test.setText("Test Connection")
            # Show error dialog on UI thread
            self._show_connection_error_dialog(desc, exc)

        run_bg(test_work, on_result=on_success, on_error=on_error)

    def _perform_connection_test(self, desc: dict, kwargs: dict) -> str:
        """Perform the actual connection test (runs in background thread)"""
        try:
            import pyodbc  # type: ignore
        except ImportError:
            # Fallback behavior without pyodbc installed
            mode = (desc.get("auth_type") or "").lower()
            extra = " Using Windows Authentication (no credential prompt)." if mode == "windows" else ""
            return "Connection settings look OK. Install 'pyodbc' to perform a live test." + extra

        conn_str = self._build_odbc_connection_string()

        # Use shorter timeout for test to prevent hanging
        timeout_sec = min(10, kwargs.get("Timeout", 5))  # Max 10 seconds
        with pyodbc.connect(conn_str, autocommit=True, timeout=timeout_sec) as _conn:  # noqa: F841
            pass

        # Windows auth does not prompt; it uses your current Windows account
        msg = "Connection succeeded."
        if self.auth_type.currentText().lower() == "windows":
            msg += " Using Windows Authentication (no credential prompt)."
        return msg

    def _show_connection_error_dialog(self, desc: dict, exc: BaseException) -> None:
        """Show connection error dialog on UI thread"""
        from src.services.mssql_connection import map_exception
        # Handle ModuleNotFoundError case
        if isinstance(exc, ModuleNotFoundError):
            # Fallback behavior without pyodbc installed
            extra = " Using Windows Authentication (no credential prompt)." if self.auth_type.currentText().lower() == "windows" else ""
            QMessageBox.information(
                self,
                "Test Connection",
                "Connection settings look OK. Install 'pyodbc' to perform a live test." + extra,
            )
            return

        # Check for Azure AD Interactive 0x534 error that can be resolved with Driver 17
        error_str = str(exc)
        if "0x534" in error_str and desc.get("auth_type") == "azure_ad_interactive":
            self._show_driver_fallback_dialog(desc, exc)
            return

        # Show error dialog with details
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Test Connection")
        box.setText(map_exception(exc))

        # Show exact driver error in Details to aid debugging
        detail = str(exc) or repr(exc)
        if detail:
            box.setInformativeText("Driver error details are available below.")
            box.setDetailedText(detail)

        box.exec()

    def _show_driver_fallback_dialog(self, desc: dict, exc: BaseException) -> None:
        """Show Azure AD 0x534 error dialog with option to retry with Driver 17"""
        from PySide6.QtWidgets import QMessageBox, QPushButton

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Test Connection")

        # Create the main error message
        error_text = ("Azure AD Interactive authentication failed (code 0x534). This is a known issue with ODBC "
                     "Driver 18. Possible solutions:\n"
                     "1. Ensure port 1433 is open in your firewall\n"
                     "2. Try using ODBC Driver 17 instead of Driver 18\n"
                     "3. Verify your AAD user has database access (CREATE USER FROM EXTERNAL PROVIDER)\n"
                     "4. Check if MSAL (Microsoft Authentication Library) is properly installed\n\n"
                     "Share the correlation ID with your admin if the issue persists.")

        box.setText(error_text)

        # Add detailed error information
        detail = str(exc) or repr(exc)
        if detail:
            box.setInformativeText("Driver error details are available below.")
            box.setDetailedText(detail)

        # Add custom buttons
        retry_driver17_btn = box.addButton("Try Driver 17", QMessageBox.ActionRole)
        ok_btn = box.addButton("OK", QMessageBox.AcceptRole)

        box.exec()

        # Handle user choice
        if box.clickedButton() == retry_driver17_btn:
            self._retry_with_driver17(desc)

    def _retry_with_driver17(self, desc: dict) -> None:
        """Retry connection test using ODBC Driver 17"""
        from src.services.background_runner import run_bg

        def test_work():
            """Test connection with Driver 17 (runs in background thread)"""
            try:
                import pyodbc
                conn_str = self._build_odbc_connection_string_for_desc_driver17(desc)
                timeout_sec = 10  # Max 10 seconds for test
                with pyodbc.connect(conn_str, autocommit=True, timeout=timeout_sec):
                    pass
                return "success"
            except Exception as e:
                return str(e)

        def on_complete(result):
            """Handle test completion (runs on UI thread)"""
            if result == "success":
                QMessageBox.information(
                    self,
                    "Test Connection",
                    "Connection succeeded using ODBC Driver 17!\n\n"
                    "Note: Your project will use Driver 17 for Azure AD authentication."
                )
                # Mark test as successful and remember to use Driver 17
                self._test_ok = True
                self._use_driver17 = True
                self.btn_ok.setEnabled(True)
            else:
                QMessageBox.critical(
                    self,
                    "Test Connection",
                    f"Connection failed even with Driver 17:\n\n{result}\n\n"
                    "Please check your connection settings and Azure AD configuration."
                )

        # Run test in background
        run_bg(test_work, on_result=on_complete)

