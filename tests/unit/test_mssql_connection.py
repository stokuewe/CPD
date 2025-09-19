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

