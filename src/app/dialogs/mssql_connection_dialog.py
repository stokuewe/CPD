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
        # Support Windows, SQL, and Azure AD modes (Interactive, Password, Integrated SSO, Device Code)
        self.auth_type.addItems(["windows", "sql", "azure_ad_interactive", "azure_ad_password", "azure_ad_integrated", "azure_ad_device_code"])  # default: windows
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        form.addRow("Server", self.server)
        form.addRow("Database", self.database)
        form.addRow("Port", self.port)
        form.addRow("Auth Type", self.auth_type)
        form.addRow("Username", self.username)
        self.authority = QLineEdit()

        form.addRow("Tenant (Authority)", self.authority)

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
        self.btn_ok.setEnabled(False)

        # Wiring
        self.btn_test.clicked.connect(self.on_test)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.auth_type.currentTextChanged.connect(self._on_auth_type_changed)

        # Invalidate test when fields change
        for w in (self.server, self.database, self.port, self.username, self.password, self.authority):
            w.textChanged.connect(self._invalidate_test)
        self.auth_type.currentTextChanged.connect(self._invalidate_test)

        # Initialize auth-dependent field state
        self._on_auth_type_changed(self.auth_type.currentText())

    def _invalidate_test(self, *args) -> None:
        self._test_ok = False
        self.btn_ok.setEnabled(False)

    def _on_auth_type_changed(self, auth: str) -> None:
        mode = (auth or "").lower()
        if mode == "windows":
            self.username.setEnabled(False)
            self.password.setEnabled(False)
            self.username.clear()
            self.password.clear()
        elif mode == "sql":
            self.username.setEnabled(True)
            self.password.setEnabled(True)
        elif mode == "azure_ad_interactive":
            # Username optional (UPN hint), password not used
            self.username.setEnabled(True)
            self.password.setEnabled(False)
            self.password.clear()
        elif mode == "azure_ad_password":
            self.username.setEnabled(True)
            self.password.setEnabled(True)
        elif mode == "azure_ad_integrated":
            # Pure SSO; no explicit credentials
            self.username.setEnabled(False)
            self.password.setEnabled(False)
            self.username.clear()
            self.password.clear()
        elif mode == "azure_ad_device_code":
            # Username optional (UPN hint), password not used
            self.username.setEnabled(True)
            self.password.setEnabled(False)
            self.password.clear()
        else:
            # Default safe state
            self.username.setEnabled(False)
            self.password.setEnabled(False)
            self.password.clear()

    def descriptor(self) -> dict:
        d: dict = {
            "server": self.server.text().strip(),
            "database": self.database.text().strip(),
            "auth_type": self.auth_type.currentText(),
        }
        # Optional fields
        try:
            port_val = int(self.port.text()) if self.port.text().strip() else None
        except ValueError:
            port_val = None
        if port_val is not None:
            d["port"] = port_val
        # Authority / Tenant (optional)
        if self.authority.text().strip():
            d["authority"] = self.authority.text().strip()
        mode = d.get("auth_type", "").lower()
        if mode in ("sql", "azure_ad_password", "azure_ad_interactive", "azure_ad_device_code"):
            if self.username.text().strip():
                d["username"] = self.username.text().strip()
            # password intentionally not stored in descriptor
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
            if mode == "azure_ad_password":
                if not desc.get("username") or not self.password.text():
                    raise ValueError("Username and Password are required for Azure AD (password) authentication")
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

        # Try a real connection if pyodbc is available; otherwise do a dry validation
        try:
            import pyodbc  # type: ignore

            conn_str = self._build_odbc_connection_string()
            # Attempt a short-lived connection; no state changes
            timeout_sec = kwargs.get("Timeout", 5)
            with pyodbc.connect(conn_str, autocommit=True, timeout=timeout_sec) as _conn:  # noqa: F841
                pass
            # Windows auth does not prompt; it uses your current Windows account
            msg = "Connection succeeded."
            if self.auth_type.currentText().lower() == "windows":
                msg += " Using Windows Authentication (no credential prompt)."
            QMessageBox.information(self, "Test Connection", msg)
            # Gate passed
            self._test_ok = True
            self.btn_ok.setEnabled(True)
        except ModuleNotFoundError:
            # Fallback behavior without pyodbc installed
            extra = " Using Windows Authentication (no credential prompt)." if self.auth_type.currentText().lower() == "windows" else ""
            QMessageBox.information(
                self,
                "Test Connection",
                "Connection settings look OK. Install 'pyodbc' to perform a live test." + extra,
            )
        except Exception as exc:  # Map to actionable message with exact error in details
            # Fallbacks: handle unsupported Authentication/Authority attributes gracefully
            msg_text = str(exc) or ""
            mode = (desc.get("auth_type") or "").lower()

            # Device Code not supported by installed driver → try Interactive
            dc_not_supported = (
                "Invalid value for the 'Authentication' connection string attribute" in msg_text
                or "Ungültiger Wert für das Attribut 'Authentication'" in msg_text
            )
            if mode == "azure_ad_device_code" and dc_not_supported:
                try:
                    temp_desc = dict(desc)
                    temp_desc["auth_type"] = "azure_ad_interactive"
                    kwargs2 = build_connect_kwargs(temp_desc)
                    conn_str2 = self._build_odbc_connection_string_for_desc(temp_desc)
                    import pyodbc  # type: ignore
                    with pyodbc.connect(conn_str2, autocommit=True, timeout=kwargs2.get("Timeout", 30)) as _conn:  # noqa: F841
                        pass
                    QMessageBox.information(
                        self,
                        "Test Connection",
                        "Connection succeeded using Azure AD Interactive (Device Code not supported by installed ODBC driver).",
                    )
                    self._test_ok = True
                    self.btn_ok.setEnabled(True)
                    return
                except Exception as exc2:
                    exc = exc2
                    msg_text = str(exc2) or msg_text

            # Authority invalid/unsupported → retry without Authority hint
            has_authority = bool(desc.get("authority"))
            authority_issue = (
                ("Authority" in msg_text and "Invalid value" in msg_text)
                or ("Authority" in msg_text and "Ungültig" in msg_text)
            )
            if mode.startswith("azure_ad") and has_authority and authority_issue:
                try:
                    temp_desc2 = dict(desc)
                    temp_desc2.pop("authority", None)
                    kwargs3 = build_connect_kwargs(temp_desc2)
                    conn_str3 = self._build_odbc_connection_string_for_desc(temp_desc2)
                    import pyodbc  # type: ignore
                    with pyodbc.connect(conn_str3, autocommit=True, timeout=kwargs3.get("Timeout", 30)) as _conn:  # noqa: F841
                        pass
                    QMessageBox.information(
                        self,
                        "Test Connection",
                        "Connection succeeded without Authority override (driver rejected provided Authority).",
                    )
                    self._test_ok = True
                    self.btn_ok.setEnabled(True)
                    return
                except Exception as exc3:
                    exc = exc3
                    msg_text = str(exc3) or msg_text
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Test Connection")
            box.setText(map_exception(exc))
            detail = msg_text or repr(exc)
            if detail:
                box.setInformativeText("Driver error details are available below.")
                box.setDetailedText(detail)
            box.exec()

