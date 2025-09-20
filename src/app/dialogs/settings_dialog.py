from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
)

from src.services.app_context import app_context


class SettingsDialog(QDialog):
    """Simple settings dialog for general project settings (M1).

    Currently includes:
    - Enable/Disable DB event logging to the Log pane
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("General"))

        self.chk_db_logging = QCheckBox("Enable DB event logging in Log pane")
        layout.addWidget(self.chk_db_logging)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

        self._load_state()

    def _load_state(self) -> None:
        # Default: enabled ("1") if not set
        val: Optional[str] = app_context.get_setting("ui_db_logging", None)
        enabled = True if val is None else str(val).strip().lower() in {"1", "true", "on", "yes"}
        self.chk_db_logging.setChecked(enabled)

    def save_state(self) -> None:
        enabled = self.chk_db_logging.isChecked()
        # Persist as "1"/"0"
        app_context.set_setting("ui_db_logging", "1" if enabled else "0")

