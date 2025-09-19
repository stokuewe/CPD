from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping

SEVERITY_MAP: Mapping[int, str] = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warning",
    logging.ERROR: "error",
    logging.CRITICAL: "critical",
}


@dataclass(slots=True)
class GuiLogRecord:
    message: str
    level: str
    timestamp: str
    logger: str

    @classmethod
    def from_record(cls, record: logging.LogRecord) -> "GuiLogRecord":
        level = SEVERITY_MAP.get(record.levelno, "info")
        timestamp = datetime.fromtimestamp(record.created, timezone.utc).isoformat()
        return cls(
            message=record.getMessage(),
            level=level,
            timestamp=timestamp,
            logger=record.name,
        )


class QtSignalHandler(logging.Handler):
    """Forward log records to a GUI emitter callback."""

    def __init__(self, emitter: Callable[[GuiLogRecord], None]) -> None:
        super().__init__()
        self._emitter = emitter

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        try:
            gui_record = GuiLogRecord.from_record(record)
            self._emitter(gui_record)
        except Exception:  # pragma: no cover - defensive bridge
            self.handleError(record)


def build_gui_handler(emitter: Callable[[GuiLogRecord], None]) -> QtSignalHandler:
    return QtSignalHandler(emitter)


__all__ = ["GuiLogRecord", "QtSignalHandler", "build_gui_handler", "SEVERITY_MAP"]
