from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6 import QtCore, QtWidgets

from src.core.errors import UserFacingError
from src.ui import message_dialogs


@dataclass(slots=True)
class MssqlConnectionParams:
    server: str
    database: str
    auth_type: str
    username: str | None
    password: str | None
    port: int | None
    driver: str

    def as_dict(self) -> dict[str, object]:
        return {
            "server": self.server,
            "database": self.database,
            "auth_type": self.auth_type,
            "username": self.username,
            "password": self.password,
            "port": self.port,
            "driver": self.driver,
        }


class MssqlParamsDialog(QtWidgets.QDialog):
    connection_verified_changed = QtCore.Signal(bool)

    def __init__(
        self,
        connection_tester: Callable[[dict[str, object]], None],
        *,
        initial: Optional[MssqlConnectionParams] = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("MSSQL Connection Parameters")
        self._tester = connection_tester
        self._verified = False

        self._server_edit = QtWidgets.QLineEdit(initial.server if initial else "")
        self._database_edit = QtWidgets.QLineEdit(initial.database if initial else "")
        self._port_edit = QtWidgets.QLineEdit(str(initial.port) if initial and initial.port else "")
        self._driver_edit = QtWidgets.QLineEdit(initial.driver if initial else "ODBC Driver 18 for SQL Server")

        self._auth_combo = QtWidgets.QComboBox()
        self._auth_combo.addItems(["sql", "windows"])
        if initial:
            index = self._auth_combo.findText(initial.auth_type)
            if index >= 0:
                self._auth_combo.setCurrentIndex(index)

        username = initial.username if initial and initial.username else ""
        password = initial.password if initial and initial.password else ""
        self._username_edit = QtWidgets.QLineEdit(username)
        self._password_edit = QtWidgets.QLineEdit(password)
        self._password_edit.setEchoMode(QtWidgets.QLineEdit.Password)

        form = QtWidgets.QFormLayout()
        form.addRow("Server", self._server_edit)
        form.addRow("Database", self._database_edit)
        form.addRow("Port", self._port_edit)
        form.addRow("Driver", self._driver_edit)
        form.addRow("Authentication", self._auth_combo)
        form.addRow("Username", self._username_edit)
        form.addRow("Password", self._password_edit)

        self._status_label = QtWidgets.QLabel("Connection not tested")
        self._status_label.setObjectName("statusLabel")

        test_button = QtWidgets.QPushButton("Test Connection")
        test_button.clicked.connect(self._test_connection)

        reset_button = QtWidgets.QPushButton("Reset")
        reset_button.clicked.connect(self._reset_verification)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._status_label)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(test_button)
        button_row.addWidget(reset_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        layout.addWidget(button_box)

        self._auth_combo.currentTextChanged.connect(self._on_auth_changed)
        self._on_auth_changed(self._auth_combo.currentText())

        for widget in (
            self._server_edit,
            self._database_edit,
            self._port_edit,
            self._driver_edit,
            self._username_edit,
            self._password_edit,
        ):
            widget.textChanged.connect(lambda _=None: self._reset_verification())

    @property
    def connection_verified(self) -> bool:
        return self._verified

    def params(self) -> MssqlConnectionParams:
        return MssqlConnectionParams(
            server=self._server_edit.text().strip(),
            database=self._database_edit.text().strip(),
            auth_type=self._auth_combo.currentText(),
            username=self._username_edit.text().strip() or None,
            password=self._password_edit.text() or None,
            port=int(self._port_edit.text()) if self._port_edit.text().strip() else None,
            driver=self._driver_edit.text().strip() or "ODBC Driver 18 for SQL Server",
        )

    def accept(self) -> None:  # type: ignore[override]
        if not self._server_edit.text().strip() or not self._database_edit.text().strip():
            message_dialogs.show_error(self, "Missing Parameters", "Server and database are required.")
            return
        if self._auth_combo.currentText() == "sql" and not self._username_edit.text().strip():
            message_dialogs.show_error(self, "Missing Credentials", "Username is required for SQL authentication.")
            return
        super().accept()

    def _test_connection(self) -> None:
        params = self.params()
        try:
            self._tester(params.as_dict())
        except UserFacingError as exc:  # pragma: no cover - user feedback path
            self._verified = False
            self._status_label.setText("Connection failed.")
            self.connection_verified_changed.emit(False)
            message_dialogs.show_user_error(self, exc)
        except Exception as exc:  # pragma: no cover - user feedback path
            self._verified = False
            self._status_label.setText("Connection failed.")
            self.connection_verified_changed.emit(False)
            message_dialogs.show_error(
                self,
                "Connection Failed",
                str(exc) or "Unexpected error while testing MSSQL connection.",
            )
        else:
            self._verified = True
            self._status_label.setText("Connection verified.")
            self.connection_verified_changed.emit(True)
            message_dialogs.show_info(
                self,
                "Connection Successful",
                "MSSQL connection succeeded.",
            )

    def _reset_verification(self) -> None:
        if self._verified:
            self.connection_verified_changed.emit(False)
        self._verified = False
        self._status_label.setText("Connection not tested")

    def _on_auth_changed(self, auth: str) -> None:
        is_sql = auth == "sql"
        self._username_edit.setEnabled(is_sql)
        self._password_edit.setEnabled(is_sql)
        self._reset_verification()


__all__ = ["MssqlParamsDialog", "MssqlConnectionParams"]
