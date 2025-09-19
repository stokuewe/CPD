from __future__ import annotations

from pathlib import Path

import pytest
from PySide6 import QtWidgets

from src.ui import message_dialogs
from src.ui.create_project_dialog import CreateProjectDialog
from src.ui.mssql_params_dialog import MssqlConnectionParams


@pytest.mark.integration
def test_create_mssql_project_requires_successful_connection_probe(
    qt_app: QtWidgets.QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(message_dialogs, "show_warning", lambda *_, **__: None)
    tester_calls: list[dict[str, object]] = []

    def tester(params: dict[str, object]) -> None:
        tester_calls.append(params)

    dialog = CreateProjectDialog(tester)
    try:
        dialog._path_edit.setText(str(tmp_path / "remote.sqlite"))  # type: ignore[attr-defined]
        for button in dialog._storage_mode_group.buttons():  # type: ignore[attr-defined]
            if dialog._storage_mode_group.id(button) == 1:  # type: ignore[attr-defined]
                button.setChecked(True)

        dialog.accept()
        assert dialog.result() == QtWidgets.QDialog.DialogCode.Rejected
        assert not tester_calls

        params = MssqlConnectionParams(
            server="localhost",
            database="demo",
            auth_type="sql",
            username="user",
            password="pass",
            port=1433,
            driver="ODBC Driver 18 for SQL Server",
        )
        dialog._mssql_params = params  # type: ignore[attr-defined]
        dialog._on_connection_verified(True)  # type: ignore[attr-defined]

        dialog.accept()
        assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
        assert dialog.mssql_params() == params.as_dict()
        assert dialog.storage_mode() == "mssql"
    finally:
        dialog.deleteLater()
