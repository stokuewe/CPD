from __future__ import annotations

import abc
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Optional, Sequence


# Unified error taxonomy (import and raise these across the app)
class DatabaseError(Exception):
    """Base class for all storage errors surfaced to the app layer."""


class TransientError(DatabaseError):
    """Retryable, typically due to load/failover (e.g., MSSQL 40501/40197)."""


class AuthError(DatabaseError):
    """Authentication or token errors (e.g., Azure AD FA004, 18456)."""


class PermissionError(DatabaseError):  # type: ignore[override]
    """Authorization/permission denied (not Python's built-in)."""


class NotFoundError(DatabaseError):
    """Missing database/table/object or resource not present."""


class ConflictError(DatabaseError):
    """Constraint violations (unique/foreign key) or conflicting state."""


class TimeoutError(DatabaseError):  # type: ignore[override]
    """Operation timed out."""


class ValidationError(DatabaseError):
    """Bad input that violates expectations (non-transient)."""


class ProgrammingError(DatabaseError):
    """Programming/SQL mistakes (bad SQL, wrong params)."""


class OperationalError(DatabaseError):
    """Operational problems not otherwise classified."""


# Mapping helpers (adapters can reuse these)
_SQLITE_NOT_FOUND_PAT = re.compile(r"no such (?:table|column|index):", re.IGNORECASE)
_SQLITE_LOCKED_PAT = re.compile(r"database is locked", re.IGNORECASE)


def map_sqlite_exception(exc: BaseException) -> DatabaseError:
    if isinstance(exc, sqlite3.IntegrityError):
        return ConflictError(str(exc))
    if isinstance(exc, sqlite3.OperationalError):
        msg = str(exc)
        if _SQLITE_NOT_FOUND_PAT.search(msg):
            return NotFoundError(msg)
        if _SQLITE_LOCKED_PAT.search(msg):
            return TransientError(msg)
        return OperationalError(msg)
    if isinstance(exc, sqlite3.ProgrammingError):
        return ProgrammingError(str(exc))
    if isinstance(exc, sqlite3.DatabaseError):
        return OperationalError(str(exc))
    return DatabaseError(str(exc))


def _is_transient_mssql_code(code: Optional[int]) -> bool:
    if code is None:
        return False
    return code in {40501, 40613, 40197} or (49918 <= code <= 49920)


def map_mssql_error(message: str, code: Optional[int] = None, sqlstate: Optional[str] = None) -> DatabaseError:
    """Best-effort mapping for MSSQL/pyodbc-style errors without importing pyodbc.

    Args:
        message: Full error text (may contain provider codes like FA004).
        code: SQL Server error number if available (e.g., 40501).
        sqlstate: SQLSTATE (e.g., '28000' for auth failures).
    """
    msg = message or ""
    # Authentication signals
    if (sqlstate == "28000") or ("FA004" in msg) or ("Login failed" in msg) or ("18456" in msg):
        return AuthError(msg)
    # Permission / access
    if "permission" in msg.lower() or "is not authorized" in msg.lower():
        return PermissionError(msg)
    # Database not accessible / missing
    if "Cannot open database" in msg or "does not exist" in msg:
        return NotFoundError(msg)
    # Transient service issues
    if _is_transient_mssql_code(code) or "temporarily unavailable" in msg.lower() or "service is busy" in msg.lower():
        return TransientError(msg)
    # Timeouts
    _low = msg.lower()
    if ("timeout" in _low) or ("timed out" in _low):
        return TimeoutError(msg)
    # Fallback
    return OperationalError(msg)


# Gateway interface
@dataclass(frozen=True)
class GatewayConfig:
    backend: str  # 'sqlite' | 'mssql'
    # SQLite
    sqlite_path: Optional[str] = None
    # MSSQL
    server: Optional[str] = None
    database: Optional[str] = None
    auth_type: Optional[str] = None  # 'sql', 'windows', 'azure_ad_*'
    username: Optional[str] = None
    authority: Optional[str] = None
    timeout_seconds: int = 30
    use_driver17: bool = False  # For Azure AD Driver 17 fallback


class DatabaseGateway(abc.ABC):
    """Unified database access facade. All DB I/O goes through this interface."""

    def __init__(self) -> None:
        self._backend = "unknown"
        self._observer = None  # Optional[Callable[[dict], None]]

    @property
    def backend(self) -> str:
        return self._backend

    # Observability hook -------------------------------------------------
    def set_observer(self, observer) -> None:
        """Install an optional observer callable(event_dict) for DB ops metrics/logs."""
        self._observer = observer

    def _notify(self, event: dict) -> None:
        cb = self._observer
        if not cb:
            return
        try:
            cb(event)
        except Exception:
            # Never let logging/observers break DB paths
            pass

    @abc.abstractmethod
    def init(self, cfg: GatewayConfig) -> None:
        """Initialize and prepare the gateway for use.
        - SQLite: open and configure a long-lived connection
        - MSSQL: validate config and prepare for per-op connections
        """

    @abc.abstractmethod
    def close(self) -> None:
        """Dispose resources. For SQLite, close the long-lived connection."""

    @abc.abstractmethod
    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Execute a statement and return affected row count."""

    @abc.abstractmethod
    def query_all(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        """Run a SELECT and return all rows as tuples."""

    @abc.abstractmethod
    def query_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[tuple]:
        """Run a SELECT and return a single row or None."""

    @abc.abstractmethod
    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Context manager providing a transactional boundary.
        Usage:
            with gateway.transaction():
                gateway.execute(...)
        """
        yield

    @abc.abstractmethod
    def health_check(self) -> None:
        """Raise DatabaseError if backend not reachable/ready."""
        raise NotImplementedError

