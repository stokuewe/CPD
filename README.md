# Construction Project Desktop ? Milestone M1

Construction Project Desktop (CPD) is a Windows-only PySide6 application that lets users create or open construction projects backed by a user-owned SQLite settings database with optional MSSQL project storage. Milestone M1 delivers the foundational startup experience: recent projects list, project creation/open flows, logging panel, and safe migrations.

## Prerequisites
- Windows 10/11
- Python 3.13 installed and available on `PATH`
- (Optional) Microsoft SQL Server instance for remote-mode validation

## Environment Setup
```powershell
# Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Or run the helper script
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
```

## Running the Application
```powershell
.\.venv\Scripts\activate
python -m src.app.main
```
The startup window provides quick access to recent projects, creation/open actions, and a live log panel. Remote MSSQL projects open in read-only mode if the server is unreachable, with clear UI and log feedback.

## Testing
```powershell
.\.venv\Scripts\activate
pytest
```
Integration tests require a GUI-capable environment (PySide6). Set `QT_QPA_PLATFORM=offscreen` for headless runs.

## Developer Utilities
- `scripts/bootstrap.ps1` ? bootstrap per the Quickstart instructions
- `scripts/validate_quickstart.ps1` ? verify the Quickstart validation checklist is up-to-date

## Documentation Map
- `specs/001-milestone-m1-basic/quickstart.md` ? manual validation steps
- `docs/architecture/m1-overview.md` ? component overview and data flow for M1
- `specs/001-milestone-m1-basic/tasks.md` ? task breakdown for the milestone
