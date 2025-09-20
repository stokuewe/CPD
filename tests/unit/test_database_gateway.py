from __future__ import annotations

import sqlite3
import pytest

from src.services.database_gateway import (
    DatabaseGateway,
    GatewayConfig,
    DatabaseError,
    TransientError,
    AuthError,
    PermissionError,
    NotFoundError,
    ConflictError,
    TimeoutError,
    ProgrammingError,
    OperationalError,
    map_sqlite_exception,
    map_mssql_error,
)


def test_error_hierarchy():
    assert issubclass(TransientError, DatabaseError)
    assert issubclass(AuthError, DatabaseError)
    assert issubclass(PermissionError, DatabaseError)
    assert issubclass(NotFoundError, DatabaseError)
    assert issubclass(ConflictError, DatabaseError)
    assert issubclass(TimeoutError, DatabaseError)
    assert issubclass(ProgrammingError, DatabaseError)
    assert issubclass(OperationalError, DatabaseError)


def test_map_sqlite_exception_conflict():
    exc = sqlite3.IntegrityError("UNIQUE constraint failed: t.name")
    mapped = map_sqlite_exception(exc)
    assert isinstance(mapped, ConflictError)


def test_map_sqlite_exception_not_found():
    exc = sqlite3.OperationalError("no such table: t")
    mapped = map_sqlite_exception(exc)
    assert isinstance(mapped, NotFoundError)


def test_map_sqlite_exception_locked_transient():
    exc = sqlite3.OperationalError("database is locked")
    mapped = map_sqlite_exception(exc)
    assert isinstance(mapped, TransientError)


def test_map_mssql_error_auth_by_code_and_message():
    # Typical auth failures
    mapped1 = map_mssql_error("Login failed for user", 18456, "28000")
    assert isinstance(mapped1, AuthError)
    mapped2 = map_mssql_error("FA004 Azure AD authentication error", None, None)
    assert isinstance(mapped2, AuthError)


def test_map_mssql_error_transient_by_code():
    mapped = map_mssql_error("The service is busy", 40501, None)
    assert isinstance(mapped, TransientError)


def test_map_mssql_error_timeout():
    mapped = map_mssql_error("Operation timed out after 30 seconds", None, None)
    assert isinstance(mapped, TimeoutError)


def test_gateway_is_abstract():
    with pytest.raises(TypeError):
        DatabaseGateway()  # abstract class cannot be instantiated


class _DummyGateway(DatabaseGateway):
    def init(self, cfg: GatewayConfig) -> None:
        self._backend = cfg.backend

    def close(self) -> None:
        pass

    def execute(self, sql: str, params=()):
        return 0

    def query_all(self, sql: str, params=()):
        return []

    def query_one(self, sql: str, params=()):
        return None

    from contextlib import contextmanager

    @contextmanager
    def transaction(self):
        yield

    def health_check(self) -> None:
        return None


def test_dummy_gateway_satisfies_interface():
    g = _DummyGateway()
    g.init(GatewayConfig(backend="sqlite"))
    assert g.backend == "sqlite"
    assert g.execute("select 1") == 0
    assert g.query_all("select 1") == []
    assert g.query_one("select 1") is None
    with g.transaction():
        rc = g.execute("update t set c=?", (1,))
        assert rc == 0
    assert g.health_check() is None

