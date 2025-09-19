import pytest

from src.lib.redaction import redact, redact_connection_string


def test_redact_password_kv():
    s = "Server=host;Database=db;User Id=sa;Password=SuperSecret123;"
    out = redact(s)
    assert "Password=***" in out
    assert "SuperSecret123" not in out


def test_redact_uri_credentials():
    s = "mssql://user:pass123@server.example.com/db"
    out = redact_connection_string(s)
    assert "user:***@" in out
    assert "pass123" not in out


def test_redact_token_like_values():
    s = "token=abc123 apikey=deadbeef api_key=shhh"
    out = redact(s)
    assert "token=***" in out
    assert "apikey=***" in out
    assert "api_key=***" in out

