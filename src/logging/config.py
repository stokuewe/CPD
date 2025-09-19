from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

JSON_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
SENSITIVE_KEYS = {"password", "pwd", "secret", "token"}
REDACTED_VALUE = "***REDACTED***"
_STANDARD_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
}


class SensitiveDataFilter(logging.Filter):
    """Redact common sensitive keys from log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        for key in SENSITIVE_KEYS:
            if hasattr(record, key):
                setattr(record, key, REDACTED_VALUE)
        if isinstance(record.args, dict):
            record.args = {
                key: (REDACTED_VALUE if key in SENSITIVE_KEYS else value)
                for key, value in record.args.items()
            }
        return True


class JsonFormatter(logging.Formatter):
    """Emit log records as compact JSON for deterministic parsing."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extras = self._extract_extras(record)
        if extras:
            payload["context"] = extras
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, ensure_ascii=True)

    def _extract_extras(self, record: logging.LogRecord) -> dict[str, Any]:
        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key.startswith("_"):
                continue
            if key in SENSITIVE_KEYS:
                extras[key] = REDACTED_VALUE
            else:
                extras[key] = self._stringify(value)
        return extras

    @staticmethod
    def _stringify(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)


def configure_logging(
    gui_handler_factory: Optional[Callable[[], logging.Handler]] = None,
    *,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure root logger with structured output and optional GUI bridge."""

    root = logging.getLogger()
    root.setLevel(level)

    if not any(isinstance(f, SensitiveDataFilter) for f in root.filters):
        root.addFilter(SensitiveDataFilter())

    if not _has_stream_handler(root.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(JsonFormatter(JSON_LOG_FORMAT))
        root.addHandler(stream_handler)

    if gui_handler_factory:
        try:
            gui_handler = gui_handler_factory()
        except Exception as exc:  # pragma: no cover - defensive placeholder
            logging.getLogger(__name__).warning(
                "Failed to initialize GUI log handler: %s", exc, exc_info=True
            )
        else:
            gui_handler.setFormatter(JsonFormatter(JSON_LOG_FORMAT))
            root.addHandler(gui_handler)

    return root


def _has_stream_handler(handlers: list[logging.Handler]) -> bool:
    return any(isinstance(handler, logging.StreamHandler) for handler in handlers)


__all__ = ["JsonFormatter", "configure_logging", "SensitiveDataFilter", "REDACTED_VALUE"]
