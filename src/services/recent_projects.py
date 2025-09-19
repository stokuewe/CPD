from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DEFAULT_LIMIT = 15


@dataclass(slots=True)
class RecentProjectEntry:
    path: Path
    last_opened: datetime

    def as_payload(self) -> dict[str, str]:
        timestamp = self.last_opened.astimezone(timezone.utc).strftime(ISO_FORMAT)
        return {"path": str(self.path), "lastOpened": timestamp}


def load_once(storage_path: Path, *, limit: int = DEFAULT_LIMIT) -> List[RecentProjectEntry]:
    if not storage_path.exists():
        return []

    try:
        payload = json.loads(storage_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    entries: List[RecentProjectEntry] = []
    for item in payload:
        try:
            raw_path = Path(item["path"])
            timestamp = _parse_timestamp(item["lastOpened"])
        except (KeyError, TypeError, ValueError):
            continue
        entries.append(RecentProjectEntry(path=raw_path, last_opened=timestamp))
    entries.sort(key=lambda entry: entry.last_opened, reverse=True)
    return entries[:limit]


def add_entry(
    entries: List[RecentProjectEntry],
    new_entry: RecentProjectEntry,
    *,
    limit: int = DEFAULT_LIMIT,
) -> List[RecentProjectEntry]:
    key = _key_for(new_entry.path)
    filtered = [entry for entry in entries if _key_for(entry.path) != key]
    combined = [new_entry, *filtered]
    return combined[:limit]


def save(
    storage_path: Path,
    entries: Iterable[RecentProjectEntry],
    *,
    limit: int = DEFAULT_LIMIT,
) -> None:
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    trimmed = list(entries)[:limit]
    serialized = [entry.as_payload() for entry in trimmed]
    storage_path.write_text(json.dumps(serialized, ensure_ascii=True, indent=2), encoding="utf-8")


def _key_for(path: Path) -> str:
    return os.path.normcase(str(path.expanduser().absolute()))


def _parse_timestamp(value: str) -> datetime:
    base = datetime.strptime(value, ISO_FORMAT)
    return base.replace(tzinfo=timezone.utc)


__all__ = ["RecentProjectEntry", "load_once", "add_entry", "save", "DEFAULT_LIMIT"]
