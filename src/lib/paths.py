"""Paths utilities for CPD (M1)

- Resolves the user-scope application data directory
- Provides the canonical path for the recent projects list file

Note: Windows-only per constitution. Avoids extra deps and uses %APPDATA%.
"""
from __future__ import annotations

import os
from pathlib import Path


_APP_DIR_NAME = "CPD"
_RECENT_LIST_FILENAME = "recent_projects.json"


def get_user_app_data_dir() -> Path:
    """Return the user-scope application data directory for CPD.

    Prefers %APPDATA% (Roaming). Falls back to ~/AppData/Roaming if unset.
    """
    appdata = os.getenv("APPDATA")
    if appdata:
        base = Path(appdata)
    else:
        # Fallback path on Windows if APPDATA not set
        base = Path.home() / "AppData" / "Roaming"
    return base / _APP_DIR_NAME


def ensure_user_app_data_dir() -> Path:
    """Ensure the user app data directory exists and return it."""
    p = get_user_app_data_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def recent_projects_path() -> Path:
    """Return the full path to the recent projects list JSON file."""
    return ensure_user_app_data_dir() / _RECENT_LIST_FILENAME


def is_unc_path(p: str | os.PathLike[str]) -> bool:
    """Return True if the given path string is a UNC path (\\\\server\\share...)."""
    s = str(p)
    return s.startswith("\\\\")


def normalize_project_path(p: str | os.PathLike[str]) -> str:
    """Normalize a project path for comparisons and storage.

    - Expands user (~)
    - Makes absolute (without requiring the path to exist)
    - Normalizes case on Windows (via os.path.normcase)
    """
    # Resolve without requiring existence; Path.resolve(strict=False) keeps symlinks if any
    abs_path = Path(p).expanduser().resolve(strict=False)
    return os.path.normcase(str(abs_path))
