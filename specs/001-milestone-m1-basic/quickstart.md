# Quickstart (M1)

This quickstart outlines how to validate M1 behavior manually once implemented.

## Pre-requisites
- Windows 10/11
- Python 3.13

## Scenarios to Validate

1) Startup view
- Launch the application
- Expect: Startup shows recent projects list and buttons to Open and Create

2) Open existing project (SQLite)
- Choose a valid .sqlite project (with meta.schema_version)
- Expect: Schema check runs; if compatible, project opens; log shows success
- If outdated: migration runs with progress; on success, project opens; on failure, clear error and no open

3) Create new project (Local Mode)
- Choose save location; keep default Local (SQLite)
- Expect: Project created; settings stored locally; log shows confirmation

4) Create new project (Remote Mode)
- Choose Remote (MSSQL); enter Server, Database, (optional Port), Auth type
- Use Test Connection
  - On success: proceed to create project; log shows confirmation
  - On failure: actionable error; cannot proceed
- Expect: Project created; connection descriptor stored locally (no password)

5) Recent projects list
- After successful open/create, restart app
- Expect: Recent list includes the project; duplicates removed; max 10 items
- Use Clear Recent; expect list is empty and persists after restart

6) Logging and redaction
- Trigger a failed MSSQL connection (e.g., wrong server)
- Expect: Log shows error with remediation; no password or full connection string logged

7) Responsiveness
- Induce a long migration (test DB with multiple steps)
- Expect: Busy indicator >200 ms; progress dialog >1 s with cancel where safe

## Notes
- No schema changes are introduced by M1; behavior must conform to sqlite.sql and azure.sql.
- Passwords are not stored in M1; prompts occur per connection attempt.

