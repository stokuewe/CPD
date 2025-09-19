"""Redaction utilities for logs.

Policies (M1):
- Never log passwords or full connection strings
- Provide helpers to scrub common patterns before logging
"""
from __future__ import annotations

import re
from typing import Pattern

# Precompiled patterns (case-insensitive)
_PWD_KV: Pattern[str] = re.compile(r"(?i)\b(password|pwd)\s*=\s*[^;\s]+")
# URI-style credentials: scheme://user:pass@host
_URI_CRED: Pattern[str] = re.compile(r"(?i)(://)([^:@\s]+):([^@\s]+)@")
# Basic bearer/API token-like sequences (very conservative)
_TOKEN: Pattern[str] = re.compile(r"(?i)\b(token|apikey|api_key)\s*=\s*[^;\s]+")


def redact(text: str | None) -> str:
    """Redact sensitive tokens in an arbitrary text string.

    Replacements:
    - password=*** / pwd=*** (key=value)
    - scheme://user:***@host (URI creds)
    - token/apikey=*** (key=value)
    """
    if not text:
        return ""
    s = text
    s = _PWD_KV.sub(lambda m: f"{m.group(0).split('=')[0]}=***", s)
    s = _URI_CRED.sub(lambda m: f"{m.group(1)}{m.group(2)}:***@", s)
    s = _TOKEN.sub(lambda m: f"{m.group(0).split('=')[0]}=***", s)
    return s


def redact_connection_string(conn: str | None) -> str:
    """Specifically target connection string patterns for logging."""
    return redact(conn)

