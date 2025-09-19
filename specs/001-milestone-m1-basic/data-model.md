# Phase 1: Data Model (Conceptual)

Note: No schema changes allowed. This model maps app concepts to the existing schemas (sqlite.sql, azure.sql) without altering them.

## Entities

### Project Settings (SQLite, always present)
- project_name: text
- storage_mode: enum { sqlite, mssql }
- created_at: timestamp
- last_opened_at: timestamp
- schema_version: semantic version string (e.g., 1.0.0)
- remote_descriptor_id: FK to MSSQL Connection Descriptor (if Remote Mode)

Behavior:
- Read/write from the local settings database file associated with the project
- On open, validate schema_version; migrate if older; refuse if newer

### Recent Project Entry (local, user-scope file)
- path: absolute project settings DB path
- last_opened: ISO-like timestamp string

Behavior:
- Maintain capped list (10)
- Move-to-top on re-open; drop missing files

### Connection Descriptor (Remote Mode, stored locally)
- server: string
- database: string
- port: optional number (default used if omitted)
- auth_type: enum { sql, windows }
- username: optional (SQL auth)
- password: not stored (prompt per connect in M1)
- secure: boolean (default on)
- trust_server_certificate: boolean override (explicit consent)
- connect_timeout_seconds: number (reasonable default)

Behavior:
- Test Connection validates credentials and connectivity before project creation/open
- Secrets are never logged; errors are actionable and redacted

## Relationships
- Project Settings (1) may reference Connection Descriptor (0..1)
- Recent Project Entry is independent of DB schemas and persisted in a user-scope file

## Validation Rules
- storage_mode must be one of { sqlite, mssql }
- path (Recent Project) must resolve to an existing file when loading the list; on add, normalization is applied
- Connection Descriptor requires server+database; if auth_type=sql then username+password (password provided at connect time)

## Notes
- All operations must conform to both sqlite.sql and azure.sql; no schema modifications are introduced by M1
- IFC-related entities are out of scope for M1 (per project roadmap)
