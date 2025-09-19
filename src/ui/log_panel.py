from __future__ import annotations

from typing import Dict

from PySide6 import QtCore, QtGui, QtWidgets

from src.logging.gui_bridge import GuiLogRecord

SEVERITY_COLOR: Dict[str, QtGui.QColor] = {
    "info": QtGui.QColor("#274060"),
    "warning": QtGui.QColor("#665200"),
    "error": QtGui.QColor("#7a1f1f"),
    "critical": QtGui.QColor("#601010"),
    "debug": QtGui.QColor("#2f2f2f"),
}


class LogPanel(QtWidgets.QWidget):
    """Simple list-based log display with severity styling."""

    MAX_ITEMS = 500

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._list = QtWidgets.QListWidget(self)
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self._list.setFocusPolicy(QtCore.Qt.NoFocus)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.setContentsMargins(0, 0, 0, 0)

    @QtCore.Slot(object)
    def append_record(self, record: GuiLogRecord) -> None:
        text = f"[{record.timestamp}] {record.level.upper()} {record.logger}: {record.message}"
        item = QtWidgets.QListWidgetItem(text)
        color = SEVERITY_COLOR.get(record.level, QtGui.QColor("#ffffff"))
        item.setBackground(color)
        self._list.addItem(item)
        self._list.scrollToBottom()
        if self._list.count() > self.MAX_ITEMS:
            self._list.takeItem(0)

    def clear(self) -> None:
        self._list.clear()


__all__ = ["LogPanel"]
