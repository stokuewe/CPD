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
        timeout = 30
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
    elif auth_type == "azure_ad_interactive":
        # Azure AD (Interactive) via ODBC Driver 18
        kwargs["Authentication"] = "ActiveDirectoryInteractive"
        if descriptor.get("username"):
            kwargs["UID"] = descriptor["username"]  # Optional UPN hint
    elif auth_type == "azure_ad_integrated":
        # Azure AD Integrated (SSO)
        kwargs["Authentication"] = "ActiveDirectoryIntegrated"
        # No UID/PWD required; driver attempts SSO with logged-in identity
    elif auth_type == "azure_ad_device_code":
        # Azure AD Device Code (browserless interactive)
        kwargs["Authentication"] = "ActiveDirectoryDeviceCode"
        if descriptor.get("username"):
            kwargs["UID"] = descriptor["username"]  # Optional UPN hint
    elif auth_type == "azure_ad_password":
        # Azure AD (Username/Password) — password supplied only at connect time
        kwargs["Authentication"] = "ActiveDirectoryPassword"
        if descriptor.get("username"):
            kwargs["UID"] = descriptor["username"]
    else:
        # If unspecified, assume windows auth for developer convenience
        kwargs["Trusted_Connection"] = "yes"

    # Port handling: if provided, append to server (common pyodbc pattern)
    port = descriptor.get("port")
    if port and isinstance(port, int):
        if "Server" in kwargs and "," not in str(kwargs["Server"]):
            kwargs["Server"] = f"{kwargs['Server']},{port}"

    # Optional Azure AD Authority/Tenant hint (driver may ignore or reject; UI has fallback)
    authority = descriptor.get("authority")
    if authority:
        kwargs["Authority"] = authority

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

    if "windows logins are not supported" in mlow:
        return (
            "Windows Authentication is not supported by the target SQL Server (e.g., Azure SQL). "
            "Switch Auth Type to 'sql' and provide a SQL user and password, or use a supported Azure AD method."
        )

    if "azure active directory only authentication is enabled" in mlow:
        return (
            "The server is configured for Azure AD-only authentication. SQL logins are rejected. "
            "Ask your administrator to enable SQL authentication (Mixed mode) or provide an Azure AD connection method."
        )

    if "fa004" in mlow:
        if "0x4b0" in mlow or "invalid_grant" in mlow or "basic_action" in mlow:
            return (
                "Azure AD (password) authentication failed: invalid credentials or tenant policy (ROPC) blocked. "
                "Use 'azure_ad_interactive' or 'azure_ad_integrated', or contact your admin."
            )
        if "0x534" in mlow:
            return (
                "Azure AD (interactive) authentication failed (code 0x534). "
                "Ensure you signed into the correct tenant and that your AAD user has access to the database. "
                "Ask an admin to CREATE USER FROM EXTERNAL PROVIDER and assign roles. Share the correlation Id with your admin."
            )
        return (
            "Azure AD authentication failed. Complete the sign-in prompt and verify your account has access; "
            "share the correlation Id with your administrator if the issue persists."
        )

    # Generic fallback
    return "Connection failed. Verify server, database, and credentials."

