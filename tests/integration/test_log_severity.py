from __future__ import annotations

from datetime import datetime, timezone

import pytest
from PySide6 import QtWidgets

from src.logging.gui_bridge import GuiLogRecord
from src.ui.log_panel import LogPanel


@pytest.mark.integration
def test_log_panel_differentiates_severity_levels(
    qt_app: QtWidgets.QApplication,
) -> None:
    panel = LogPanel()
    try:
        records = [
            GuiLogRecord("info message", "info", datetime.now(timezone.utc).isoformat(), "logger"),
            GuiLogRecord("warning message", "warning", datetime.now(timezone.utc).isoformat(), "logger"),
            GuiLogRecord("error message", "error", datetime.now(timezone.utc).isoformat(), "logger"),
        ]
        for record in records:
            panel.append_record(record)

        colors = [panel._list.item(index).background().color().name().lower() for index in range(3)]  # type: ignore[attr-defined]
        assert colors[0] == "#274060"
        assert colors[1] == "#665200"
        assert colors[2] == "#7a1f1f"
    finally:
        panel.deleteLater()
