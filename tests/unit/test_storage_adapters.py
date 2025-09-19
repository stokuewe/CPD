from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from src.core.errors import (
    ConnectionAuthenticationError,
    ConnectionFailureError,
    ConnectionTimeoutError,
)
from src.storage.mssql_adapter import MSSQLAdapter, MSSQLProfile
from src.storage.sqlite_adapter import SQLiteAdapter


def test_sqlite_adapter_executes_script_and_queries(tmp_path: Path) -> None:
    db_path = tmp_path / "project.sqlite"
    adapter = SQLiteAdapter(db_path)

    adapter.execute_script(
        """
        CREATE TABLE items(id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO items(name) VALUES ('alpha');
        """
    )

    rows = adapter.query("SELECT name FROM items")
    assert rows == [{"name": "alpha"}]

    adapter.begin()
    adapter.execute("INSERT INTO items(name) VALUES (?)", ("beta",))
    adapter.rollback()
    rows_after = adapter.query("SELECT COUNT(*) AS count FROM items")
    assert rows_after == [{"count": 1}]

    adapter.close()


def test_mssql_adapter_translate_timeout() -> None:
    profile = MSSQLProfile(server="example", database="db", auth_type="sql")
    adapter = MSSQLAdapter(profile)

    class DummyError(Exception):
        def __init__(self, *args: str) -> None:
            super().__init__(*args)
            self.args = args

    timeout_exc = DummyError("[HYT00]", "timeout occurred")
    mapped = adapter._translate_exception(timeout_exc)  # type: ignore[attr-defined]
    assert isinstance(mapped, ConnectionTimeoutError)


def test_mssql_adapter_translate_auth_failure() -> None:
    profile = MSSQLProfile(server="example", database="db", auth_type="sql")
    adapter = MSSQLAdapter(profile)

    class DummyError(Exception):
        def __init__(self, *args: str) -> None:
            super().__init__(*args)
            self.args = args

    auth_exc = DummyError("[28000]", "Login failed for user")
    mapped = adapter._translate_exception(auth_exc)  # type: ignore[attr-defined]
    assert isinstance(mapped, ConnectionAuthenticationError)


def test_mssql_adapter_translate_generic_failure() -> None:
    profile = MSSQLProfile(server="example", database="db", auth_type="sql")
    adapter = MSSQLAdapter(profile)

    class DummyError(Exception):
        def __init__(self, *args: str) -> None:
            super().__init__(*args)
            self.args = args

    failure_exc = DummyError("[08001]", "General network error")
    mapped = adapter._translate_exception(failure_exc)  # type: ignore[attr-defined]
    assert isinstance(mapped, ConnectionFailureError)


def test_mssql_adapter_sanitized_profile_masks_credentials() -> None:
    profile = MSSQLProfile(
        server="srv",
        database="demo",
        auth_type="sql",
        username="user",
        password="secret",
        port=1444,
    )
    adapter = MSSQLAdapter(profile)

    sanitized = adapter.sanitized_profile()
    assert sanitized == {
        "server": "srv",
        "database": "demo",
        "auth_type": "sql",
        "username": "user",
        "port": 1444,
        "driver": "ODBC Driver 18 for SQL Server",
    }
