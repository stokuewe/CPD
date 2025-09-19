from __future__ import annotations

class UserFacingError(Exception):
    """Base exception carrying user-presentable context."""

    def __init__(self, message: str, *, title: str, remediation: str | None = None) -> None:
        super().__init__(message)
        self.title = title
        self.remediation = remediation or ""


class ProjectCreationError(UserFacingError):
    pass


class ProjectOpenError(UserFacingError):
    pass


class MigrationBlockedError(UserFacingError):
    pass


class ConnectionTimeoutError(UserFacingError):
    pass


class ConnectionAuthenticationError(UserFacingError):
    pass


class ConnectionFailureError(UserFacingError):
    pass


__all__ = [
    "UserFacingError",
    "ProjectCreationError",
    "ProjectOpenError",
    "MigrationBlockedError",
    "ConnectionTimeoutError",
    "ConnectionAuthenticationError",
    "ConnectionFailureError",
]
