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
    """Dialog for entering MSSQL connection details (M1 skeleton).

    Includes a Test Connection button that validates inputs and shows
    an actionable message. No passwords are persisted.
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

        self.btn_test.clicked.connect(self.on_test)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

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

    def on_test(self) -> None:  # pragma: no cover - UI interaction
        try:
            kwargs = build_connect_kwargs(self.descriptor())
            # In M1 we don't open a real connection; just validate mapping and show success
            if not kwargs.get("Server") or not kwargs.get("Database"):
                raise ValueError("Server and Database are required")
        except Exception as exc:  # show actionable message
            QMessageBox.warning(self, "Test Connection", map_exception(exc))
            return
        QMessageBox.information(self, "Test Connection", "Connection settings look OK.")

