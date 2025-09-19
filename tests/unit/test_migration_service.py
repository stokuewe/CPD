from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from src.core.errors import MigrationBlockedError
from src.services.migration_service import MigrationService, TARGET_SCHEMA_VERSION


@dataclass
class FakeAdapter:
    version: str
    script_executed: bool = False
    began: bool = False
    committed: bool = False
    rolled_back: bool = False
    queries: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)

    def connect(self) -> None:
        return None

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        self.queries.append((sql, params))
        if self.version == "missing":
            return []
        return [{"value": self.version}]

    def execute_script(self, sql: str) -> None:
        self.script_executed = True

    def begin(self) -> None:
        self.began = True

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def test_run_migrations_noop_when_up_to_date(tmp_path: Path) -> None:
    adapter = FakeAdapter(version=TARGET_SCHEMA_VERSION)
    service = MigrationService(adapter)

    result = service.run_migrations(tmp_path / "settings.sqlite")

    assert result == TARGET_SCHEMA_VERSION
    assert not adapter.script_executed
    assert not adapter.began


def test_run_migrations_executes_baseline_for_empty(tmp_path: Path) -> None:
    adapter = FakeAdapter(version="0.0.0")
    service = MigrationService(adapter)

    result = service.run_migrations(tmp_path / "settings.sqlite")

    assert adapter.script_executed
    assert adapter.began
    assert adapter.committed
    assert not adapter.rolled_back
    assert result == TARGET_SCHEMA_VERSION


def test_run_migrations_rejects_invalid_version(tmp_path: Path) -> None:
    adapter = FakeAdapter(version="2.5.0")
    service = MigrationService(adapter)

    with pytest.raises(MigrationBlockedError) as excinfo:
        service.run_migrations(tmp_path / "settings.sqlite")

    assert "Unsupported schema version" in str(excinfo.value)
