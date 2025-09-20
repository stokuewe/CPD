from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.services.db_adapters.sqlite_adapter import SqliteAdapter
from src.services.database_gateway import GatewayConfig, ConflictError, DatabaseError


def test_init_sets_pragmas(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    adapter = SqliteAdapter()
    adapter.init(GatewayConfig(backend="sqlite", sqlite_path=str(db_path)))

    # Verify PRAGMAs (using the same connection)
    conn = adapter._ensure_conn()  # type: ignore[attr-defined]
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    jm = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert str(jm).lower() == "wal"
    sync = conn.execute("PRAGMA synchronous").fetchone()[0]
    # NORMAL is 1 per docs
    assert int(sync) in (1, "1")

    adapter.close()


def test_execute_and_query(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    a = SqliteAdapter()
    a.init(GatewayConfig(backend="sqlite", sqlite_path=str(db_path)))

    a.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
    assert a.execute("INSERT INTO t(name) VALUES (?)", ("a",)) == 1
    assert a.execute("INSERT INTO t(name) VALUES (?)", ("b",)) == 1

    all_rows = a.query_all("SELECT id, name FROM t ORDER BY id")
    assert all_rows == [(1, "a"), (2, "b")]

    row = a.query_one("SELECT name FROM t WHERE id=?", (2,))
    assert row == ("b",)

    a.close()


def test_transactions_commit_and_rollback(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    a = SqliteAdapter()
    a.init(GatewayConfig(backend="sqlite", sqlite_path=str(db_path)))

    a.execute("CREATE TABLE t(x INTEGER)")

    # Commit path
    with a.transaction():
        a.execute("INSERT INTO t(x) VALUES (?)", (1,))
    assert a.query_all("SELECT x FROM t") == [(1,)]

    # Nested with inner rollback
    with a.transaction():
        a.execute("INSERT INTO t(x) VALUES (?)", (2,))
        try:
            with a.transaction():
                a.execute("INSERT INTO t(x) VALUES (?)", (3,))
                raise RuntimeError("boom")
        except RuntimeError:
            pass
    # Ensure only the outer insert remains
    assert a.query_all("SELECT x FROM t ORDER BY x") == [(1,), (2,)]

    a.close()


def test_conflict_error_mapping(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    a = SqliteAdapter()
    a.init(GatewayConfig(backend="sqlite", sqlite_path=str(db_path)))

    a.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
    a.execute("INSERT INTO t(name) VALUES (?)", ("a",))
    with pytest.raises(ConflictError):
        a.execute("INSERT INTO t(name) VALUES (?)", ("a",))

    a.close()


def test_health_check(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    a = SqliteAdapter()
    a.init(GatewayConfig(backend="sqlite", sqlite_path=str(db_path)))

    a.health_check()  # should not raise

    a.close()

