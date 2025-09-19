from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Sequence

from .adapter import Params, Row, StorageAdapter


class SQLiteAdapter(StorageAdapter):
    backend: str = "sqlite"

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> None:
        if self._connection is not None:
            return

        self._connection = sqlite3.connect(
            str(self._db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._apply_pragmas()

    def close(self) -> None:
        if self._connection is None:
            return
        self._connection.close()
        self._connection = None

    def begin(self) -> None:
        self._ensure_connection()
        assert self._connection is not None
        self._connection.execute("BEGIN")

    def commit(self) -> None:
        if self._connection is None:
            return
        self._connection.commit()

    def rollback(self) -> None:
        if self._connection is None:
            return
        self._connection.rollback()

    def execute(self, sql: str, params: Params = ()) -> sqlite3.Cursor:
        self._ensure_connection()
        assert self._connection is not None
        return self._connection.execute(sql, params)

    def executemany(self, sql: str, seq_params: Sequence[Params]) -> sqlite3.Cursor:
        self._ensure_connection()
        assert self._connection is not None
        return self._connection.executemany(sql, seq_params)

    def query(self, sql: str, params: Params = ()) -> list[Row]:
        cursor = self.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def execute_script(self, sql: str) -> None:
        self._ensure_connection()
        assert self._connection is not None
        self._connection.executescript(sql)

    def supports_feature(self, feature: str) -> bool:
        features = {
            "transactions": True,
            "wal": True,
        }
        return features.get(feature, False)

    def _ensure_connection(self) -> None:
        if self._connection is None:
            self.connect()

    def _apply_pragmas(self) -> None:
        assert self._connection is not None
        cursor = self._connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.close()


__all__ = ["SQLiteAdapter"]
