# CPD — Common Project Database (M1)

Windows desktop application (Python 3.13 + PySide6) with dual storage: local (SQLite) and optional remote (MSSQL). This repository adheres to the binding CONSTITUTION.md and synchronized schemas in sqlite.sql and azure.sql.

## Getting started

- Requirements: Windows 10/11, Python 3.13
- Install (dev):
  ```powershell
  python -m pip install --upgrade pip
  pip install .[test]
  ```

- Run the GUI (manual smoke):
  ```powershell
  python -m src.app.run
  ```
  - Recent list interactions:
    - Double-click or press Enter to open a recent project
    - Right-click → Open / Remove from Recent
    - The Open Project button opens the selected recent ONLY if you explicitly selected one; otherwise it shows a file dialog

- Run tests:
  ```powershell
  pytest -q
  ```

- Manual validation:
  See docs/quickstart-m1.md

## Project structure (high-level)

- src/lib: utilities (paths, redaction)
- src/services: core services (recent projects, migrations, connections, creators)
- src/app: PySide6 GUI (main window, controllers, dialogs)
- tests/unit, tests/integration, tests/contract
- specs/001-milestone-m1-basic: milestone specification and quickstart

## Notes

- No schema changes are permitted without prior approval; sqlite.sql and azure.sql must remain synchronized.
- Passwords and secrets are never persisted or logged; errors are redacted.

