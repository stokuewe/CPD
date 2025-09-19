from __future__ import annotations

from pathlib import Path
from typing import Optional


class ProjectLoader:
    """Placeholder for project loading logic (M1).

    Responsibilities (later milestones):
    - Open settings DB
    - Read schema_version and orchestrate migrations
    - Refuse to open if schema is newer than supported
    """

    def __init__(self, project_path: Path | str) -> None:
        self.project_path: Path = Path(project_path)
        self.schema_version: Optional[str] = None

    def open(self) -> None:
        # Implementation will be added in subsequent tasks
        raise NotImplementedError

