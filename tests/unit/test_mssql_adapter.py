from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from src.services.db_adapters.mssql_adapter import MssqlAdapter
from src.services.database_gateway import GatewayConfig, TransientError


class _FakeCursor:
    def __init__(self, script: list[tuple] | None = None):
        self._script = script or []
        self.rowcount = 1
        self._executed = []

    def execute(self, sql: str, params: tuple = ()):  # noqa: ARG002
        self._executed.append((sql, params))
        return self

    def fetchall(self):
        return list(self._script)

    def fetchone(self):
        if self._script:
            return self._script[0]
        return (1,)

    def close(self):
        pass


class _FakeConn:
    def __init__(self, script: list[tuple] | None = None, record: dict | None = None):
        self.closed = False
        self.autocommit = True
        self._script = script or []
        self._record = record if record is not None else {}
        self._committed = False
        self._rolled_back = False

    def cursor(self):
        return _FakeCursor(self._script)

    def close(self):
        self.closed = True

    def commit(self):
        self._committed = True

    def rollback(self):
        self._rolled_back = True


class _TransientExc(Exception):
    def __init__(self, message: str):
        super().__init__("[Microsoft][SQL Server] " + message)
        # Simulate pyodbc args where one might contain SQLSTATE and/or code
        self.args = ("HYT00", str(self))


def _install_fake_pyodbc(connect_impl):
    fake = SimpleNamespace(connect=connect_impl, Error=Exception)
    sys.modules["pyodbc"] = fake
    return fake


def test_per_operation_connect_and_close(monkeypatch):
    # Arrange fake pyodbc
    calls = {"count": 0}

    def connect_impl(conn_str: str, autocommit: bool, timeout: int):  # noqa: ARG001
        calls["count"] += 1
        return _FakeConn(script=[(1, "ok")])

    _install_fake_pyodbc(connect_impl)

    a = MssqlAdapter()
    a.init(GatewayConfig(backend="mssql", server="s", database="d", auth_type="windows", timeout_seconds=5))

    # Act
    rows = a.query_all("SELECT 1")

    # Assert
    assert rows == [(1, "ok")]
    assert calls["count"] == 1


def test_transaction_uses_single_connection_and_commits(monkeypatch):
    created = []

    def connect_impl(conn_str: str, autocommit: bool, timeout: int):  # noqa: ARG001
        c = _FakeConn(script=[(1,)], record={})
        created.append(c)
        return c

    _install_fake_pyodbc(connect_impl)

    a = MssqlAdapter()
    a.init(GatewayConfig(backend="mssql", server="s", database="d", auth_type="windows", timeout_seconds=5))

    with a.transaction():
        a.execute("UPDATE t SET x=?", (1,))
        a.query_one("SELECT 1")

    # Only one connection was created and it was committed
    assert len(created) == 1
    assert created[0]._committed is True
    assert created[0].closed is True


def test_health_check_skips_azure_ad_interactive_in_background_thread(monkeypatch):
    """Test that health check is skipped for Azure AD Interactive in background threads."""
    import threading

    # Create mock thread objects
    main_thread = threading.Thread(name="MainThread")
    background_thread = threading.Thread(name="BackgroundThread")

    # Mock threading functions
    monkeypatch.setattr(threading, "current_thread", lambda: background_thread)
    monkeypatch.setattr(threading, "main_thread", lambda: main_thread)

    # Mock pyodbc to avoid actual connection
    _install_fake_pyodbc(lambda *args, **kwargs: _FakeConn())

    a = MssqlAdapter()
    a.init(GatewayConfig(
        backend="mssql",
        server="test.database.windows.net",
        database="testdb",
        auth_type="azure_ad_interactive",
        username="user@domain.com"
    ))

    # Health check should be skipped and not raise an exception
    a.health_check()  # Should complete without attempting connection


def test_retry_on_transient_error_then_success(monkeypatch):
    # First call raises a transient error, second returns a conn
    state = {"i": 0}

    def connect_impl(conn_str: str, autocommit: bool, timeout: int):  # noqa: ARG001
        state["i"] += 1
        if state["i"] == 1:
            raise _TransientExc("The service is busy, please retry")
        return _FakeConn(script=[(1,)])

    _install_fake_pyodbc(connect_impl)

    a = MssqlAdapter()
    a.init(GatewayConfig(backend="mssql", server="s", database="d", auth_type="windows", timeout_seconds=1))

    # Should succeed after one retry
    assert a.query_one("SELECT 1") == (1,)

