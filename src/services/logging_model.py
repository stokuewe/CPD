from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.lib.redaction import redact


@dataclass
class LogEntry:
    level: str
    message: str


class LoggingModel:
    """Simple in-memory logging model with redaction hook (M1).

    Levels: INFO, WARN, ERROR
    """

    def __init__(self) -> None:
        self._entries: List[LogEntry] = []

    def log(self, level: str, message: str) -> None:
        lvl = level.upper()
        if lvl not in {"INFO", "WARN", "ERROR"}:
            lvl = "INFO"
        self._entries.append(LogEntry(lvl, redact(message)))

    def entries(self) -> List[LogEntry]:
        return list(self._entries)

