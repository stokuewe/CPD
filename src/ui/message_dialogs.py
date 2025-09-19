from __future__ import annotations

from pathlib import Path

from PySide6 import QtWidgets

from src.core.errors import UserFacingError


def show_error(parent: QtWidgets.QWidget, title: str, message: str) -> None:
    QtWidgets.QMessageBox.critical(parent, title, message)


def show_warning(parent: QtWidgets.QWidget, title: str, message: str) -> None:
    QtWidgets.QMessageBox.warning(parent, title, message)


def show_info(parent: QtWidgets.QWidget, title: str, message: str) -> None:
    QtWidgets.QMessageBox.information(parent, title, message)


def ask_confirmation(
    parent: QtWidgets.QWidget,
    title: str,
    message: str,
    *,
    default_yes: bool = False,
) -> bool:
    buttons = QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
    default = QtWidgets.QMessageBox.Yes if default_yes else QtWidgets.QMessageBox.No
    response = QtWidgets.QMessageBox.question(parent, title, message, buttons, default)
    return response == QtWidgets.QMessageBox.Yes


def show_backup_warning(
    parent: QtWidgets.QWidget,
    project_path: Path,
    current_version: str,
    target_version: str,
) -> None:
    message = (
        "The project at\n"
        f"{project_path}\n"
        "is using schema version "
        f"{current_version}.\n\n"
        "It will be migrated to version "
        f"{target_version}.\n"
        "Please create a backup before continuing."
    )
    show_warning(parent, "Backup Recommended", message)


def show_user_error(parent: QtWidgets.QWidget, error: UserFacingError) -> None:
    body = error.args[0] if error.args else "An error occurred."
    if error.remediation:
        body = f"{body}\n\n{error.remediation}"
    QtWidgets.QMessageBox.critical(parent, error.title, body)


__all__ = [
    "show_error",
    "show_warning",
    "show_info",
    "ask_confirmation",
    "show_backup_warning",
    "show_user_error",
]
