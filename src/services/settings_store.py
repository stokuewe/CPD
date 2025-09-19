from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ProjectSettings:
    project_name: str
    storage_mode: str  # 'sqlite' or 'mssql'
    created_at: str
    last_opened_at: str
    schema_version: str
    # Reference to remote descriptor (if any); details persisted locally excluding passwords
    remote_descriptor_id: Optional[str] = None


class SettingsStore:
    """Skeleton of settings persistence (M1). Actual DB I/O added later."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    def load(self) -> ProjectSettings:
        raise NotImplementedError

    def save(self, settings: ProjectSettings) -> None:
        raise NotImplementedError

