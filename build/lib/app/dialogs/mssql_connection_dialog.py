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
        self.auth_type.addItems(["windows", "sql"])  # default: windows
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
        self.btn_ok.setEnabled(False)

    def _on_auth_type_changed(self, auth: str) -> None:
        is_windows = (auth or "").lower() == "windows"
        # Disable user/pass for Windows Authentication; clear any entered creds
        self.username.setEnabled(not is_windows)
        self.password.setEnabled(not is_windows)
        if is_windows:
            self.username.clear()
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
        if d.get("auth_type") == "sql":
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
        if kwargs.get("Trusted_Connection") == "yes":
            parts.append("Trusted_Connection=yes")
        else:
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            # Pull password only from the field for test purposes; never persist
            pwd = self.password.text()
            if pwd:
                parts.append(f"PWD={pwd}")
        # Security defaults
        parts.append("Encrypt=yes")
        parts.append("TrustServerCertificate=no")
        # Timeout
        if kwargs.get("Timeout"):
            parts.append(f"Timeout={kwargs['Timeout']}")
        return ";".join(parts)

    def on_test(self) -> None:  # pragma: no cover - UI interaction
        # First, validate inputs/map to kwargs
        try:
            kwargs = build_connect_kwargs(self.descriptor())
            if not kwargs.get("Server") or not kwargs.get("Database"):
                raise ValueError("Server and Database are required")
        except Exception as exc:  # show actionable message
            QMessageBox.warning(self, "Test Connection", map_exception(exc))
            return

        # Try a real connection if pyodbc is available; otherwise do a dry validation
        try:
            import pyodbc  # type: ignore

            conn_str = self._build_odbc_connection_string()
            # Attempt a short-lived connection; no state changes
            with pyodbc.connect(conn_str, autocommit=True) as _conn:  # noqa: F841
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
        except Exception as exc:  # Map to actionable message
            QMessageBox.warning(self, "Test Connection", map_exception(exc))

