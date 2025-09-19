import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.services.recent_projects import (
    DEFAULT_LIMIT,
    RecentProjectEntry,
    add_entry,
    load_once,
    save,
)


@pytest.fixture()
def sample_entries(tmp_path: Path) -> list[RecentProjectEntry]:
    now = datetime.now(timezone.utc)
    entries: list[RecentProjectEntry] = []
    for index in range(DEFAULT_LIMIT):
        entries.append(
            RecentProjectEntry(
                path=tmp_path / f"project_{index}.sqlite",
                last_opened=now - timedelta(hours=index),
            )
        )
    return entries


def test_add_entry_deduplicates_and_caps(sample_entries: list[RecentProjectEntry]) -> None:
    newer = RecentProjectEntry(
        path=sample_entries[2].path,
        last_opened=datetime.now(timezone.utc),
    )
    updated = add_entry(sample_entries, newer)
    assert updated[0].path == newer.path
    assert len(updated) == DEFAULT_LIMIT
    occurrences = [entry for entry in updated if entry.path == newer.path]
    assert len(occurrences) == 1


def test_load_once_sorts_and_limits(tmp_path: Path, sample_entries: list[RecentProjectEntry]) -> None:
    storage_path = tmp_path / "recents.json"
    payload = [entry.as_payload() for entry in sample_entries]
    extra_entry = RecentProjectEntry(
        path=tmp_path / "older.sqlite",
        last_opened=datetime.now(timezone.utc) - timedelta(days=10),
    )
    payload.append(extra_entry.as_payload())
    storage_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_once(storage_path)
    assert len(loaded) == DEFAULT_LIMIT
    times = [entry.last_opened for entry in loaded]
    assert times == sorted(times, reverse=True)


def test_save_trims_to_limit(tmp_path: Path, sample_entries: list[RecentProjectEntry]) -> None:
    storage_path = tmp_path / "recent.json"
    extra_entry = RecentProjectEntry(
        path=tmp_path / "extra.sqlite",
        last_opened=datetime.now(timezone.utc),
    )
    extended = [extra_entry, *sample_entries]
    save(storage_path, extended)
    persisted = json.loads(storage_path.read_text(encoding="utf-8"))
    assert len(persisted) == DEFAULT_LIMIT
    assert persisted[0]["path"].endswith("extra.sqlite")
