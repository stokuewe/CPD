from __future__ import annotations

from typing import Dict, Any

from src.services.mssql_connection import build_connect_kwargs


class ProjectCreatorRemote:
    """Validate a remote (MSSQL) connection descriptor for a project (M1).

    Passwords are not stored; caller must prompt per connection.
    This step validates descriptor fields and secure defaults only.
    """

    def __init__(self, descriptor: Dict[str, Any]) -> None:
        self.descriptor = descriptor

    def create(self) -> None:
        # Validate descriptor via kwargs mapping
        kwargs = build_connect_kwargs(self.descriptor)
        if not kwargs.get("Server") or not kwargs.get("Database"):
            raise ValueError("Server and Database are required for Remote Mode")
        # No persistence in M1; connectivity is validated separately via Test Connection

