# Data Model – Milestone M1

Scope: Minimal schema required for startup, project creation/open, migrations baseline, remote mode configuration, and logging display state (in-memory for log window; persistent only where specified).

## Entities

### Project (implicit context, not a table)
Represents loaded project environment.
- Attributes: settings_db_path (abs path), storage_mode (enum: sqlite|mssql), schema_version (semver string), read_only (bool), opened_at (timestamp)

### meta (table)
- key TEXT PRIMARY KEY
- value TEXT NOT NULL
- Required Row: ('schema_version','1.0.0') for baseline

### settings (table)
- key TEXT PRIMARY KEY
- value TEXT NOT NULL
- Expected keys (M1): 'project_name', 'storage_mode', 'created_at'

### mssql_connection (table; present only if storage_mode = mssql)
- id INTEGER PRIMARY KEY CHECK (id=1)
- server TEXT NOT NULL
- database TEXT NOT NULL
- port INTEGER DEFAULT 1433
- auth_type TEXT CHECK (auth_type IN ('sql','windows')) NOT NULL
- username TEXT NULL (required if auth_type='sql')
- password TEXT NULL (NOT persisted in M1 unless unavoidable; placeholder column defined for forward compatibility)

### recent_projects.json (file)
Array of objects:
```
[
  { "path": "C:/abs/project1.sqlite", "lastOpened": "2025-09-19T12:34:56Z" },
  ... (max 15)
]
```

### LogEntry (in-memory only)
- timestamp (ISO 8601 string)
- level (INFO|WARNING|ERROR)
- message (string)
- context (optional small object: operation, path, mode)

## Relationships
- One Project references zero-or-one mssql_connection record (only when storage_mode='mssql').
- recent_projects.json contains references to potential Project roots but is not authoritative for validity.

## Derived / Computed
- read_only flag derived at load: storage_mode='mssql' AND connection failure → True.

## Validation Rules
- storage_mode ∈ { 'sqlite','mssql' }
- If storage_mode='mssql': mssql_connection row must exist with non-empty server & database; username required if auth_type='sql'.
- schema_version must match application supported baseline (exact equality for M1).

## Migration Baseline (M1)
Baseline script ensures meta/settings/mssql_connection definitions exist (latter optional). Future versions append ordered migration scripts.

## Persistence Notes
- Only SQLite DB and recent_projects.json persist on disk in M1.
- Sensitive secrets (password) intentionally not persisted; user re-enters per session when needed.

## Constitution Alignment
- Single authoritative SQLite file for settings and optional remote profile.
- No dual writes of project domain data (none defined yet).

