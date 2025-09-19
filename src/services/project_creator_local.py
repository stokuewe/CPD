from __future__ import annotations

from pathlib import Path
import sqlite3


class ProjectCreatorLocal:
    """Creates a new local (SQLite) project settings DB by applying sqlite.sql."""

    def __init__(self, target_path: Path | str) -> None:
        self.target_path = Path(target_path)

    def create(self) -> None:
        # Guard: do not overwrite existing DB file
        if self.target_path.exists():
            raise FileExistsError(f"Target already exists: {self.target_path}")

        # Locate schema script at repository root
        repo_root = Path(__file__).resolve().parents[2]
        schema_path = repo_root / "sqlite.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"sqlite.sql not found at {schema_path}")

        sql = schema_path.read_text(encoding="utf-8")

        # Ensure parent directory exists
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

        # Create DB and apply schema
        with sqlite3.connect(str(self.target_path)) as conn:
            conn.executescript(sql)
            conn.commit()

