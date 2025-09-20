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

        # Actually test the connection to ensure it works
        self._test_connection()

    def _test_connection(self) -> None:
        """Test the actual database connection to ensure credentials work."""
        try:
            import pyodbc  # type: ignore
        except ImportError:
            # If pyodbc is not available, skip the connection test
            # This maintains backward compatibility
            return

        # Build connection string similar to the dialog test
        from src.services.db_adapters.mssql_adapter import _build_conn_str
        from src.services.database_gateway import GatewayConfig

        # Convert descriptor to GatewayConfig format
        cfg = GatewayConfig(
            backend="mssql",
            server=self.descriptor.get("server"),
            database=self.descriptor.get("database"),
            auth_type=self.descriptor.get("auth_type", "windows"),
            username=self.descriptor.get("username"),
            authority=self.descriptor.get("authority"),
            timeout_seconds=10  # Short timeout for validation
        )

        try:
            # Check if we should use Driver 17 (from successful dialog fallback)
            if self.descriptor.get("use_driver17"):
                conn_str = self._build_conn_str_driver17(cfg)
            else:
                conn_str = _build_conn_str(cfg)

            # For SQL authentication, add password to connection string if provided
            if (self.descriptor.get("auth_type", "").lower() == "sql" and
                self.descriptor.get("password")):
                if "PWD=" not in conn_str:
                    conn_str += f";PWD={self.descriptor.get('password')}"

            # Test connection with short timeout
            with pyodbc.connect(conn_str, autocommit=True, timeout=10) as conn:
                # Simple query to verify connection works
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if not result or result[0] != 1:
                    raise RuntimeError("Connection test query failed")
        except Exception as exc:
            # Re-raise with a clear message about connection failure
            raise RuntimeError(f"Connection test failed: {exc}") from exc

    def _build_conn_str_driver17(self, cfg) -> str:
        """Build connection string using ODBC Driver 17 for Azure AD compatibility"""
        from src.services.mssql_connection import build_connect_kwargs

        # Convert descriptor to kwargs for consistency
        desc = {
            "server": cfg.server,
            "database": cfg.database,
            "auth_type": cfg.auth_type,
            "username": cfg.username,
            "authority": cfg.authority,
        }
        kwargs = build_connect_kwargs(desc)

        parts = ["DRIVER={ODBC Driver 17 for SQL Server}"]  # Use Driver 17

        if kwargs.get("Server"):
            parts.append(f"SERVER={kwargs['Server']}")
        if kwargs.get("Database"):
            parts.append(f"DATABASE={kwargs['Database']}")

        auth_type = (desc.get("auth_type") or "").lower()
        if auth_type == "windows" or kwargs.get("Trusted_Connection") == "yes":
            parts.append("Trusted_Connection=yes")
        elif auth_type == "sql":
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            # Password will be added by caller if needed
        elif auth_type == "azure_ad_interactive":
            parts.append("Authentication=ActiveDirectoryInteractive")
            if kwargs.get("UID"):
                parts.append(f"UID={kwargs['UID']}")
            if desc.get("authority"):
                parts.append(f"Authority={desc['authority']}")
        elif auth_type == "azure_ad_integrated":
            parts.append("Authentication=ActiveDirectoryIntegrated")

        # Azure AD requires encryption
        if auth_type.startswith("azure_ad"):
            parts.append("Encrypt=yes")
            parts.append("TrustServerCertificate=yes")

        return ";".join(parts)

