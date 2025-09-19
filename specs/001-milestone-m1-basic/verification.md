# Milestone M1 Verification Checklist

| Requirement | Implementation References | Validation |
|-------------|----------------------------|------------|
| FR-001 & FR-007 (Startup options, create flow) | `src/ui/startup_window.py:16`, `src/ui/create_project_dialog.py:16` | Manual Quickstart steps 2?8; `tests/integration/test_startup_perf.py:33` ensures window constructs rapidly |
| FR-002 & FR-021 (Recent projects persistence, cap) | `src/services/recent_projects.py:11`, `src/services/project_service.py:402` | `tests/unit/test_recent_projects.py:21` |
| FR-003?FR-006 (SQLite migration/open safety) | `src/services/migration_service.py:13`, `src/services/project_service.py:181` | `tests/unit/test_migration_service.py:16` |
| FR-009?FR-016 (MSSQL setup, read-only fallback) | `src/services/project_service.py:132`, `src/services/project_service.py:349`, `src/storage/mssql_adapter.py:28` | `tests/unit/test_storage_adapters.py:40`, Quickstart checklist items |
| FR-012 & FR-017 (Log severity + major operation logging) | `src/ui/log_panel.py:11`, `src/logging/config.py:35`, `src/services/project_service.py:63` | `tests/unit/test_logging_bridge.py:4`, log review via Quickstart |
| FR-018 & FR-028 (Rollback on failure, migration logging) | `src/services/project_service.py:205`, `src/services/migration_service.py:33` | `tests/unit/test_migration_service.py:55` |
| FR-024 & FR-025 (Credential redaction, actionable messaging) | `src/logging/config.py:35`, `src/core/errors.py:3`, `src/ui/message_dialogs.py:53` | Quickstart checklist item ?No secrets exposed in logs?, manual error dialogs |
| FR-027 (Migration locking) | `src/services/project_service.py:52` (re-entrant lock around operations) | Manual verification during Quickstart migration scenario |

## Automation Artifacts
- `pytest` (unit & integration smoke). Unit suites cover recent projects, migrations, storage adapters, logging bridge.
- `scripts/validate_quickstart.ps1` validates that manual checklist entries remain present.

## Manual Checklist
Run `specs/001-milestone-m1-basic/quickstart.md` end-to-end and confirm:
- SQLite project creation + reopen
- MSSQL parameter validation + read-only fallback messaging
- Migration warning and log entries
- Recent list cap and clear action
- Logs omit sensitive fields

Record outcomes and attach logs/screenshots when complete.
