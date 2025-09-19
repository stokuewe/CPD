# GUI Interaction Contracts (M1)

Contracts define user-facing actions, inputs, outputs, and errors. They are implementation-agnostic.

## Action: Show Startup View
- Inputs: none
- Preconditions: App launches on Windows; config storage accessible
- Outputs: Startup window with recent list and actions: Open Project, Create Project, Clear Recent
- Errors: If recent list cannot be read, show warning and render empty list

## Action: Open Existing Project
- Inputs: absolute path to a project settings SQLite file
- Preconditions: File path resolves; readable by the app
- Flow:
  1) Read schema_version from project metadata
  2) If older than supported: run sequential migrations with progress
  3) If newer than supported: refuse to open; instruct to upgrade app
  4) On success: project context loaded; recent list updated (move-to-top)
- Outputs: Project opened
- Errors:
  - Corrupt or incompatible DB — clear error; do not open
  - Migration failure — clear error; do not open

## Action: Create New Project (Local Mode)
- Inputs: save location
- Preconditions: Destination directory writable
- Flow: Initialize settings DB; set storage_mode=sqlite; write initial metadata
- Outputs: Project created
- Errors: IO errors — clear error; do not create

## Action: Create New Project (Remote Mode)
- Inputs: server, database, (optional) port, auth_type, username/password (if SQL auth)
- Preconditions: Network reachable; credentials provided as per auth_type
- Flow:
  1) Test Connection must succeed prior to creation
  2) Initialize settings DB; set storage_mode=mssql; store connection descriptor excluding password
- Outputs: Project created
- Errors:
  - Connection test failure — actionable error; do not create
  - IO errors — clear error; do not create

## Action: Test MSSQL Connection
- Inputs: server, database, (optional) port, auth_type, username/password (if SQL auth)
- Preconditions: Inputs provided
- Outputs: Success or actionable error message (redacted)
- Errors:
  - Timeout/unreachable
  - Auth failure
  - Certificate trust issue (offer explicit developer override)

## Action: Clear Recent
- Inputs: none
- Preconditions: Recent list exists (may be empty)
- Flow: Replace stored list with empty array
- Outputs: Recent list cleared; UI updated
- Errors: IO errors — warning; list rendered empty

