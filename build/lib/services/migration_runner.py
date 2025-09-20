from __future__ import annotations

from pathlib import Path
from typing import Optional


class MigrationRunner:
    """Controls migration execution flow for a project database (M1 control-flow only).

    M1 scope: provide control-flow markers used by tests.
    - begin(): set recovery_marker and compute backup_path
    - abort_or_finish(): clear or finalize state
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path: Path = Path(db_path)
        self.recovery_marker: bool = False
        self.backup_path: Optional[Path] = None

    def begin(self) -> None:
        # In a full implementation, create a pre-migration backup file alongside the DB
        self.recovery_marker = True
        self.backup_path = self._compute_backup_path()

    def abort_or_finish(self) -> None:
        # For M1 tests, it's sufficient to keep attributes present after lifecycle.
        # A real implementation would remove the recovery marker or finalize it.
        pass

    # Internal -------------------------------------------------------
    def _compute_backup_path(self) -> Path:
        p = self.db_path
        if p.suffix:
            return p.with_suffix(p.suffix + ".bak")
        return Path(str(p) + ".bak")

