from __future__ import annotations

from typing import Dict, Any


def build_connect_kwargs(descriptor: Dict[str, Any]) -> Dict[str, Any]:
    """Return pyodbc.connect keyword args from a connection descriptor.

    Defaults:
    - Encrypt=True (secure by default)
    - TrustServerCertificate=False (explicit developer override required)
    - Timeout: reasonable default if not provided (5 seconds)
    """
    kwargs: Dict[str, Any] = {}

    server = descriptor.get("server")
    database = descriptor.get("database")
    if server:
        kwargs["Server"] = server
    if database:
        kwargs["Database"] = database

    # Security defaults
    kwargs.setdefault("Encrypt", True)
    kwargs.setdefault("TrustServerCertificate", False)

    # Connection timeout (seconds)
    timeout = descriptor.get("connect_timeout_seconds")
    if timeout is None:
        timeout = 5
    kwargs["Timeout"] = timeout

    # Auth
    auth_type = (descriptor.get("auth_type") or "").lower()
    if auth_type == "windows":
        kwargs["Trusted_Connection"] = "yes"
    elif auth_type == "sql":
        # Username provided here; password must be supplied at connect time
        if descriptor.get("username"):
            kwargs["UID"] = descriptor["username"]
        # Do not include password in kwargs for logging safety (M1 policy)
    else:
        # If unspecified, assume windows auth for developer convenience
        kwargs["Trusted_Connection"] = "yes"

    # Port handling: if provided, append to server (common pyodbc pattern)
    port = descriptor.get("port")
    if port and isinstance(port, int):
        if "Server" in kwargs and "," not in str(kwargs["Server"]):
            kwargs["Server"] = f"{kwargs['Server']},{port}"

    return kwargs


def map_exception(exc: BaseException) -> str:
    """Map low-level exceptions to actionable, redacted messages.

    Requirements for tests:
    - TimeoutError -> mention unreachable/timeout
    - Certificate issues -> mention certificate and override/trust hint
    - Never include sensitive credentials in message
    """
    msg = str(exc) if exc else ""
    mlow = msg.lower()

    if isinstance(exc, TimeoutError) or "timeout" in mlow or "timed out" in mlow:
        return (
            "Connection attempt timed out or server unreachable. "
            "Verify server/port, network/VPN, and firewall settings."
        )

    if "certificate" in mlow or "ssl" in mlow:
        return (
            "TLS certificate validation failed. For development, you may "
            "enable a temporary trust override (Trust Server Certificate) "
            "with explicit consent. Use secure settings in production."
        )

    # Generic fallback
    return "Connection failed. Verify server, database, and credentials."

