from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import pyodbc

from src.core.errors import (
    ConnectionAuthenticationError,
    ConnectionFailureError,
    ConnectionTimeoutError,
)

from .adapter import Params, Row, StorageAdapter


@dataclass(slots=True)
class MSSQLProfile:
    server: str
    database: str
    auth_type: str
    username: str | None = None
    password: str | None = None
    port: int | None = None
    driver: str = "ODBC Driver 18 for SQL Server"


class MSSQLAdapter(StorageAdapter):
    backend: str = "mssql"

    def __init__(self, profile: MSSQLProfile, *, timeout: int = 5) -> None:
        self._profile = profile
        self._timeout = timeout
        self._connection: pyodbc.Connection | None = None

    def connect(self) -> None:
        if self._connection is not None:
            return
        conn_str = self._build_connection_string()
        try:
            self._connection = pyodbc.connect(conn_str, timeout=self._timeout, autocommit=False)
        except pyodbc.Error as exc:  # pragma: no cover - connection failure path
            raise self._translate_exception(exc) from exc

    def close(self) -> None:
        if self._connection is None:
            return
        self._connection.close()
        self._connection = None

    def begin(self) -> None:
        self._ensure_connection()
        self.execute("BEGIN TRANSACTION")

    def commit(self) -> None:
        if self._connection is None:
            return
        self._connection.commit()

    def rollback(self) -> None:
        if self._connection is None:
            return
        self._connection.rollback()

    def execute(self, sql: str, params: Params = ()) -> pyodbc.Cursor:
        self._ensure_connection()
        assert self._connection is not None
        cursor = self._connection.cursor()
        try:
            cursor.execute(sql, params)
        except pyodbc.Error as exc:  # pragma: no cover - SQL execution error path
            raise self._translate_exception(exc) from exc
        return cursor

    def executemany(self, sql: str, seq_params: Sequence[Params]) -> pyodbc.Cursor:
        self._ensure_connection()
        assert self._connection is not None
        cursor = self._connection.cursor()
        try:
            cursor.executemany(sql, seq_params)
        except pyodbc.Error as exc:  # pragma: no cover - SQL execution error path
            raise self._translate_exception(exc) from exc
        return cursor

    def query(self, sql: str, params: Params = ()) -> list[Row]:
        cursor = self.execute(sql, params)
        columns = [column[0] for column in cursor.description or ()]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def execute_script(self, sql: str) -> None:
        raise NotImplementedError("Batch script execution not supported for MSSQL adapter")

    def supports_feature(self, feature: str) -> bool:
        features = {
            "transactions": True,
            "stored_procedures": True,
        }
        return features.get(feature, False)

    def test_connection(self) -> None:
        try:
            connection = pyodbc.connect(
                self._build_connection_string(), timeout=self._timeout, autocommit=True
            )
        except pyodbc.Error as exc:
            raise self._translate_exception(exc) from exc
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        except pyodbc.Error as exc:
            raise self._translate_exception(exc) from exc
        finally:
            connection.close()

    def _ensure_connection(self) -> None:
        if self._connection is None:
            self.connect()

    def _build_connection_string(self) -> str:
        profile = self._profile
        parts: list[str] = [f"DRIVER={{{profile.driver}}}", f"SERVER={profile.server}"]
        if profile.port:
            parts[-1] = f"{parts[-1]},{profile.port}"
        parts.append(f"DATABASE={profile.database}")
        if profile.auth_type == "sql":
            if profile.username:
                parts.append(f"UID={profile.username}")
            if profile.password:
                parts.append(f"PWD={profile.password}")
        else:
            parts.append("Trusted_Connection=yes")
        parts.append("Encrypt=yes")
        parts.append("TrustServerCertificate=yes")
        return ";".join(parts)

    def sanitized_profile(self) -> Mapping[str, Any]:
        return {
            "server": self._profile.server,
            "database": self._profile.database,
            "auth_type": self._profile.auth_type,
            "username": self._profile.username,
            "port": self._profile.port,
            "driver": self._profile.driver,
        }

    def _translate_exception(self, exc: pyodbc.Error) -> ConnectionFailureError:
        message = " ".join(str(part) for part in exc.args) or str(exc)
        lowered = message.lower()
        if "hyt00" in lowered or "timeout" in lowered:
            return ConnectionTimeoutError(
                "The connection attempt to MSSQL timed out.",
                title="Connection Timeout",
                remediation="Verify network connectivity and that the SQL Server is reachable, then retry.",
            )
        if "28000" in lowered or "login failed" in lowered:
            return ConnectionAuthenticationError(
                "Authentication with MSSQL failed.",
                title="Authentication Failed",
                remediation="Confirm username/password or Windows authentication settings and try again.",
            )
        return ConnectionFailureError(
            "Unable to establish MSSQL connection.",
            title="Connection Failed",
            remediation="Check the server address, port, and firewall settings before retrying.",
        )


__all__ = ["MSSQLAdapter", "MSSQLProfile"]
