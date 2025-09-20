import pytest


def test_connection_error_mapping_timeout():
    try:
        from src.services.mssql_connection import map_exception
    except Exception:
        pytest.fail("MSSQL connection tester not implemented yet")

    msg = map_exception(TimeoutError("timed out"))
    assert "unreachable" in msg.lower() or "timeout" in msg.lower()
    assert "password" not in msg.lower()


def test_connection_error_mapping_cert_trust():
    try:
        from src.services.mssql_connection import map_exception, build_connect_kwargs
    except Exception:
        pytest.fail("MSSQL connection tester not implemented yet")

    err = RuntimeError("certificate verify failed")
    msg = map_exception(err)
    assert "certificate" in msg.lower()
    # Ensure we expose an explicit override hint in dev scenarios
    assert "override" in msg.lower() or "trust" in msg.lower()

    # Build kwargs should default to secure settings
    kwargs = build_connect_kwargs({
        "server": "localhost",
        "database": "db",
        "auth_type": "windows",
    })
    assert kwargs.get("Encrypt", True) is True


def test_azure_ad_connection_string_generation():
    """Test that Azure AD connection strings include TrustServerCertificate=yes"""
    try:
        from src.services.db_adapters.mssql_adapter import _build_conn_str
        from src.services.database_gateway import GatewayConfig
    except Exception:
        pytest.fail("MSSQL adapter not implemented yet")

    # Test Azure AD Interactive
    cfg = GatewayConfig(
        backend="mssql",
        server="test.database.windows.net",
        database="testdb",
        auth_type="azure_ad_interactive",
        username="user@domain.com"
    )
    conn_str = _build_conn_str(cfg)

    assert "Authentication=ActiveDirectoryInteractive" in conn_str
    assert "TrustServerCertificate=yes" in conn_str
    assert "Encrypt=yes" in conn_str

    # Test non-Azure AD should still use TrustServerCertificate=no
    cfg_windows = GatewayConfig(
        backend="mssql",
        server="test.database.windows.net",
        database="testdb",
        auth_type="windows"
    )
    conn_str_windows = _build_conn_str(cfg_windows)

    assert "TrustServerCertificate=no" in conn_str_windows

