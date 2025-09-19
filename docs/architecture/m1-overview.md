# Milestone M1 Architecture Overview

## Runtime Layers
- **UI (PySide6)** ? `StartupWindow`, creation dialogs, and log panel orchestrate user interaction. UI components surface read-only state, actionable errors, and emit events back to services.
- **Services** ? `ProjectService`, `MigrationService`, and recent-project helpers coordinate persistence, migrations, connection probing, and logging. User-facing errors encode titles/remediation for the UI layer.
- **Storage Adapters** ? `SQLiteAdapter` and `MSSQLAdapter` implement a shared protocol handling connection lifecycles, transactions, and backend-specific behaviours (PRAGMAs vs. connection string construction).
- **Logging** ? Structured logging (JSON) with sensitive-data redaction feeds both stdout and the GUI log panel via `QtSignalHandler`.

## Key Flows
1. **Startup**
   - `StartupWindow` loads recent projects (max 15) from `recent_projects.json`.
   - `configure_logging` hooks the GUI handler before the window shows.

2. **Create Project**
   - UI enforces MSSQL parameter verification before submission.
   - `ProjectService.create_project` runs baseline migration, seeds settings, persists remote profile (without password), and updates recents. Failures trigger cleanup of partial SQLite files.

3. **Open Project**
   - Schema version check ? optional backup warning ? migrations (single-transaction baseline).
   - Remote projects probe MSSQL; failures switch to read-only state with UI + log messaging.

4. **Logging & Telemetry**
   - Every major operation logs start/success/failure with contextual metadata (path, mode, operation).
   - Sensitive keys (`password`, `token`, etc.) are redacted centrally.

## Persistence Artifacts
- **SQLite Settings DB** ? Stores meta/settings tables plus optional MSSQL profile row.
- **Recent Projects JSON** ? List of capped, ordered entries under `%USERPROFILE%\.cpd\recent_projects.json`.
- **Migrations** ? Baseline SQL script (`src/migrations/0001_baseline.sql`) applied via `MigrationService`.

## Error Handling Strategy
- Service layer raises `UserFacingError` variants with localized titles and remediation text.
- UI utility `show_user_error` converts these into modal dialogs while preserving log traces.
- MSSQL adapter normalizes timeout/auth/connectivity exceptions for consistent UX.

## Future Hooks
- Context capsule persistence and IFC data flows will attach alongside `ProjectState` in later milestones.
- Additional migrations will extend the paired SQLite/MSSQL architecture while reusing the existing locking and logging patterns.
