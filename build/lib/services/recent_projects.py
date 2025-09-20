from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from src.lib import paths as paths_mod

MAX_RECENT = 10


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normcase(p: str) -> str:
    # Windows-insensitive comparison; safe on other OSes too
    return os.path.normcase(os.path.abspath(p))


@dataclass
class RecentEntry:
    path: str
    last_opened: str


class RecentProjectsService:
    """Manages the Recent Projects list persisted in a user-scope file.

    - Cap: 10 entries
    - De-dup: case-insensitive by absolute path
    - Move-to-top on re-add
    - Validate on load: drop entries whose file no longer exists
    - Remove individual entries
    """

    def __init__(self) -> None:
        self._path: Path = paths_mod.recent_projects_path()
        self._data: List[RecentEntry] = []
        self._loaded: bool = False

    # Public API -----------------------------------------------------
    def clear(self) -> None:
        self._data = []
        self._save()

    def add(self, project_path: str) -> None:
        self._ensure_loaded()
        abs_path = os.path.abspath(project_path)
        key = _normcase(abs_path)

        # Remove any existing entry matching this path (case-insensitive)
        self._data = [e for e in self._data if _normcase(e.path) != key]

        # Insert at top
        self._data.insert(0, RecentEntry(path=abs_path, last_opened=_now_iso()))

        # Cap to MAX_RECENT
        self._data = self._data[:MAX_RECENT]
        self._save()

    def list(self) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        return [asdict(e) for e in self._data]

    def remove(self, project_path: str) -> None:
        """Remove an entry by path (case-insensitive)."""
        self._ensure_loaded()
        key = _normcase(os.path.abspath(project_path))
        before = len(self._data)
        self._data = [e for e in self._data if _normcase(e.path) != key]
        if len(self._data) != before:
            self._save()

    def reload(self) -> None:
        # Force reload and validate entries
        self._loaded = False
        self._ensure_loaded()

    # Internal -------------------------------------------------------
    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        raw = self._read_file()
        entries: List[RecentEntry] = []
        for item in raw:
            p = item.get("path")
            ts = item.get("last_opened") or _now_iso()
            if not p:
                continue
            # Drop entries whose file no longer exists
            if not Path(p).exists():
                continue
            entries.append(RecentEntry(path=os.path.abspath(p), last_opened=ts))
        # Deduplicate while preserving order (case-insensitive)
        seen: set[str] = set()
        deduped: List[RecentEntry] = []
        for e in entries:
            k = _normcase(e.path)
            if k in seen:
                continue
            seen.add(k)
            deduped.append(e)
        self._data = deduped[:MAX_RECENT]
        self._loaded = True
        # Persist normalized/deduped form
        self._save()

    def _read_file(self) -> List[Dict[str, Any]]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")
            return []
        try:
            return json.loads(self._path.read_text(encoding="utf-8") or "[]")
        except Exception:
            # On parse error, reset to empty
            return []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(e) for e in self._data]
        self._path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

