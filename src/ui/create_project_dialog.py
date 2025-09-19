from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6 import QtCore, QtWidgets

from src.ui import message_dialogs
from src.ui.mssql_params_dialog import MssqlConnectionParams, MssqlParamsDialog


class CreateProjectDialog(QtWidgets.QDialog):
    """Collect new project parameters, enforcing MSSQL connection verification."""

    def __init__(
        self,
        connection_tester: Callable[[dict[str, object]], None],
        *,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Project")
        self._tester = connection_tester

        self._path_edit = QtWidgets.QLineEdit()
        browse_button = QtWidgets.QPushButton("Browse...")
        browse_button.clicked.connect(self._select_path)

        path_row = QtWidgets.QHBoxLayout()
        path_row.addWidget(self._path_edit)
        path_row.addWidget(browse_button)

        self._storage_mode_group = QtWidgets.QButtonGroup(self)
        sqlite_radio = QtWidgets.QRadioButton("SQLite (local)")
        sqlite_radio.setChecked(True)
        mssql_radio = QtWidgets.QRadioButton("MSSQL (remote)")
        self._storage_mode_group.addButton(sqlite_radio, 0)
        self._storage_mode_group.addButton(mssql_radio, 1)

        mode_layout = QtWidgets.QVBoxLayout()
        mode_layout.addWidget(sqlite_radio)
        mode_layout.addWidget(mssql_radio)

        mode_group_box = QtWidgets.QGroupBox("Storage Mode")
        mode_group_box.setLayout(mode_layout)

        self._configure_mssql_button = QtWidgets.QPushButton("Configure MSSQL...")
        self._configure_mssql_button.clicked.connect(self._open_mssql_dialog)
        self._configure_mssql_button.setEnabled(False)

        self._connection_status_label = QtWidgets.QLabel("Connection not tested")
        self._connection_status_label.setObjectName("connectionStatusLabel")

        controls_layout = QtWidgets.QHBoxLayout()
        controls_layout.addWidget(self._configure_mssql_button)
        controls_layout.addWidget(self._connection_status_label)
        controls_layout.addStretch(1)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(path_row)
        layout.addWidget(mode_group_box)
        layout.addLayout(controls_layout)
        layout.addWidget(button_box)

        self._mssql_params: Optional[MssqlConnectionParams] = None
        self._connection_verified = False

        self._storage_mode_group.idToggled.connect(self._on_storage_mode_changed)
        self._on_storage_mode_changed(self._storage_mode_group.checkedId(), True)

    def selected_path(self) -> Path:
        return Path(self._path_edit.text()).expanduser().resolve()

    def storage_mode(self) -> str:
        return "mssql" if self._storage_mode_group.checkedId() == 1 else "sqlite"

    def mssql_params(self) -> Optional[dict[str, object]]:
        return self._mssql_params.as_dict() if self._mssql_params else None

    def accept(self) -> None:  # type: ignore[override]
        raw_path = self._path_edit.text().strip()
        if not raw_path:
            message_dialogs.show_error(self, "Missing Path", "Please choose a settings database path.")
            return
        path = Path(raw_path)
        if path.exists():
            message_dialogs.show_error(self, "File Exists", "The selected file already exists. Choose a new path.")
            return
        if self.storage_mode() == "mssql" and not self._connection_verified:
            message_dialogs.show_warning(
                self,
                "Connection Not Verified",
                "Please configure and verify the MSSQL connection before creating the project.",
            )
            return
        super().accept()

    def _select_path(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Choose Settings Database", str(Path.home() / "project.sqlite"), "SQLite DB (*.sqlite);;All Files (*.*)"
        )
        if file_path:
            self._path_edit.setText(file_path)

    def _open_mssql_dialog(self) -> None:
        dialog = MssqlParamsDialog(self._tester, initial=self._mssql_params, parent=self)
        dialog.connection_verified_changed.connect(self._on_connection_verified)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self._mssql_params = dialog.params()
            self._connection_verified = dialog.connection_verified
            status = "Connection verified" if self._connection_verified else "Connection not tested"
            self._connection_status_label.setText(status)
        else:
            self._connection_verified = False
            self._connection_status_label.setText("Connection not tested")

    def _on_connection_verified(self, verified: bool) -> None:
        self._connection_verified = verified
        status = "Connection verified" if verified else "Connection not tested"
        self._connection_status_label.setText(status)

    def _on_storage_mode_changed(self, mode_id: int, checked: bool) -> None:
        if not checked:
            return
        is_mssql = mode_id == 1
        self._configure_mssql_button.setEnabled(is_mssql)
        if not is_mssql:
            self._connection_verified = False
            self._connection_status_label.setText("Connection not tested")


__all__ = ["CreateProjectDialog"]
