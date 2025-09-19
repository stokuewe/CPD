from __future__ import annotations

import logging
from pathlib import Path

from src.core.errors import MigrationBlockedError
from src.storage.adapter import StorageAdapter

TARGET_SCHEMA_VERSION = "1.0.0"
BASELINE_FILE = Path(__file__).resolve().parents[1] / "migrations" / "0001_baseline.sql"


class MigrationService:
    """Coordinates detection and execution of schema migrations."""

    def __init__(self, storage_adapter: StorageAdapter) -> None:
        self._storage_adapter = storage_adapter
        self._logger = logging.getLogger(__name__)

    def check_version(self, settings_path: Path) -> str:
        del settings_path
        self._storage_adapter.connect()
        try:
            rows = self._storage_adapter.query(
                "SELECT value FROM meta WHERE key = ?", ("schema_version",)
            )
        except Exception:
            return "0.0.0"
        if not rows:
            return "0.0.0"
        return str(rows[0].get("value", "0.0.0"))

    def run_migrations(self, settings_path: Path) -> str:
        current_version = self.check_version(settings_path)
        if current_version == TARGET_SCHEMA_VERSION:
            return current_version

        if current_version not in {"0.0.0", ""}:
            raise MigrationBlockedError(
                f"Unsupported schema version: {current_version}",
                title="Unsupported Schema Version",
                remediation="Update the application or restore from a compatible backup before retrying.",
            )

        script = BASELINE_FILE.read_text(encoding="utf-8")
        self._storage_adapter.connect()
        self._logger.info(
            "Applying baseline migration",
            extra={
                "operation": "run_migrations",
                "from_version": current_version,
                "target_version": TARGET_SCHEMA_VERSION,
            },
        )
        self._storage_adapter.begin()
        try:
            self._storage_adapter.execute_script(script)
            self._storage_adapter.commit()
        except Exception as exc:
            self._storage_adapter.rollback()
            self._logger.error(
                "Migration failed",
                extra={"operation": "run_migrations", "from_version": current_version},
                exc_info=True,
            )
            raise
        else:
            self._logger.info(
                "Migration complete",
                extra={"operation": "run_migrations", "target_version": TARGET_SCHEMA_VERSION},
            )
        return TARGET_SCHEMA_VERSION


__all__ = ["MigrationService", "TARGET_SCHEMA_VERSION"]
