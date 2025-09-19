# Tasks: Milestone M1 – Basic GUI, Startup, and Database Connection

**Input**: Design documents from `/specs/001-milestone-m1-basic/`  
**Prerequisites**: `plan.md` (required), `research.md`, `data-model.md`, `quickstart.md`

## Execution Flow (main)
```
1. Load plan.md → success
2. Load data-model, research, quickstart → extracted entities & scenarios
3. Generate tasks per rules (tests precede implementation, [P] for independent files)
4. Build dependency ordering (foundations → tests → core → integration → polish)
5. Validate coverage of FR-001..FR-030
6. Output tasks.md
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (distinct files / no dependency chain)
- Tests MUST be written first and initially fail.

## Phase 3.1: Setup & Foundation
- [ ] T001 Create base source tree: `src/app/`, `src/ui/`, `src/storage/`, `src/services/`, `src/migrations/`, `src/logging/`, `tests/unit/`, `tests/integration/` (no code yet; placeholder `__init__.py` files)
- [ ] T002 Add dependency manifest `requirements.txt` (PySide6, pyodbc, IfcOpenShell placeholder, pytest) and bootstrap script `scripts/bootstrap.ps1`
- [ ] T003 Configure logging initializer `src/logging/config.py` (structured formatter + GUI bridge hook placeholder)
- [ ] T004 Define storage adapter protocol `src/storage/adapter.py` (SQLiteAdapter, MSSQLAdapter stubs) – no DB logic
- [ ] T005 Baseline migration SQL file `src/migrations/0001_baseline.sql` (meta, settings, mssql_connection tables) referencing schema_version 1.0.0
- [ ] T006 Recent projects service skeleton `src/services/recent_projects.py` (load_once(), add_entry(), save()) with no implementation
- [ ] T007 Project lifecycle service skeleton `src/services/project_service.py` (open_project, create_project signatures only)
- [ ] T008 Migration service skeleton `src/services/migration_service.py` (check_version, run_migrations placeholders)

## Phase 3.2: Tests First (TDD)
Integration/user-flow oriented based on user stories and acceptance scenarios. Each test file independent → mark [P].
- [ ] T009 [P] Test startup empty list: `tests/integration/test_startup_empty.py` (expects no recent entries, UI options present)
- [ ] T010 [P] Test create local project flow: `tests/integration/test_create_local_project.py` (creates DB, baseline schema, recent list updated)
- [ ] T011 [P] Test create MSSQL project blocked until test connection success: `tests/integration/test_create_mssql_requires_test.py`
- [ ] T012 [P] Test open existing up-to-date project: `tests/integration/test_open_project_current.py`
- [ ] T013 [P] Test open outdated project triggers backup warning + migration: `tests/integration/test_open_project_migration.py`
- [ ] T014 [P] Test open invalid file error: `tests/integration/test_open_invalid_file.py`
- [ ] T015 [P] Test read-only fallback when MSSQL unreachable: `tests/integration/test_remote_read_only_fallback.py`
- [ ] T016 [P] Test recent list de-duplication and cap at 15: `tests/integration/test_recent_list_cap.py`
- [ ] T017 [P] Test clear recent list action: `tests/integration/test_clear_recent_list.py`
- [ ] T018 [P] Test log severity differentiation (info/warn/error): `tests/integration/test_log_severity.py`

## Phase 3.3: Core Implementation (only after Phase 3.2 tests exist & fail)
- [ ] T019 Implement recent projects service logic in `src/services/recent_projects.py` (load, add, dedupe, cap, save) – FR-002, FR-014, FR-021
- [ ] T020 Implement storage adapter base + SQLiteAdapter in `src/storage/sqlite_adapter.py` (connect, execute, transaction context) – FR-003, FR-004
- [ ] T021 Implement MSSQLAdapter skeleton (connection test only) in `src/storage/mssql_adapter.py` – FR-009, FR-010 (test only path), FR-015
- [ ] T022 Implement migration service logic in `src/services/migration_service.py` (detect outdated, atomic apply baseline only) – FR-004, FR-005, FR-030
- [ ] T023 Implement project service creation logic (SQLite local) in `src/services/project_service.py` – FR-001, FR-007
- [ ] T024 Extend project service for MSSQL mode (store parameters sans password) – FR-008, FR-011, FR-024
- [ ] T025 Implement open project logic: validate path, schema_version, run migrations or block, set read-only for unreachable MSSQL – FR-003, FR-006, FR-016, FR-019, FR-020
- [ ] T026 Implement logging bridge `src/logging/gui_bridge.py` (emit to Qt signal + level mapping) – FR-012, FR-017, FR-025, FR-026
- [ ] T027 Add backup warning prompt invocation before migration (UI stub call) – FR-030, FR-025
- [ ] T028 Ensure partial project creation rollback (cleanup on failure) – FR-018
- [ ] T029 Operation locking for migration/open to prevent duplicates – FR-027
- [ ] T030 In-memory project state structure (for future context capsule) – FR-022, FR-023

## Phase 3.4: UI Layer Implementation
- [ ] T031 Startup window `src/ui/startup_window.py` (recent list display, open/create actions) – FR-001
- [ ] T032 Create project dialog `src/ui/create_project_dialog.py` (mode selection, path input) – FR-007, FR-008
- [ ] T033 MSSQL parameters dialog `src/ui/mssql_params_dialog.py` (fields + Test Connection button) – FR-009, FR-010, FR-015
- [ ] T034 Log panel widget `src/ui/log_panel.py` (severity coloring) – FR-012, FR-017
- [ ] T035 Error/warning modal `src/ui/message_dialogs.py` (backup warning, errors) – FR-006, FR-025, FR-030
- [ ] T036 Integrate UI with services in `src/app/main.py` (bootstrap, signal wiring, action handlers) – multiple FRs (001, 007, 009, 012, etc.)
- [ ] T037 Clear recent list action wiring (confirmation) – FR-013
- [ ] T038 Read-only remote indicator in UI – FR-016

## Phase 3.5: Integration & Refinement
- [ ] T039 Integrate logging config with GUI bridge (config + panel subscription) – FR-012, FR-017
- [ ] T040 Add MSSQL timeout handling + distinct messages – FR-015
- [ ] T041 Add remediation text mapping for common errors (file not found, invalid schema, connection fail) – FR-025
- [ ] T042 Validate removal of partial artifacts on failed create/open (additional edge tests) – FR-018
- [ ] T043 Enforce recent list maximum trimming logic test adjustments – FR-021
- [ ] T044 Add project state read-only flag propagation to UI – FR-016
- [ ] T045 Final pass for secrets redaction in log messages – FR-024
- [ ] T046 Confirm migration locking under rapid double-open scenario – FR-027

## Phase 3.6: Polish & Documentation
- [ ] T047 [P] Unit tests for recent_projects service `tests/unit/test_recent_projects.py`
- [ ] T048 [P] Unit tests for migration service edge cases `tests/unit/test_migration_service.py`
- [ ] T049 [P] Unit tests for storage adapters `tests/unit/test_storage_adapters.py`
- [ ] T050 [P] Unit tests for logging bridge `tests/unit/test_logging_bridge.py`
- [ ] T051 Performance sanity (startup <2s, test harness) `tests/integration/test_startup_perf.py`
- [ ] T052 Quickstart validation script `scripts/validate_quickstart.ps1` referencing quickstart steps
- [ ] T053 Update `README.md` with M1 setup & run instructions
- [ ] T054 Internal developer doc `docs/architecture/m1-overview.md` summarizing services & flow
- [ ] T055 Remove unused stubs / tighten type hints across new modules
- [ ] T056 Final verification checklist run (map FRs to code/tests)

## Dependencies
- T001–T008 foundational (sequential order recommended) before writing tests that import them.
- Tests T009–T018 precede corresponding implementation tasks (T019+).
- T019 (recent projects service) precedes T031 integration of list display.
- T022 migration service precedes T025 open logic & T027 backup warning.
- T020/T021 adapters precede T023/T024/T025 project service logic.
- UI tasks depend on service implementations (T019–T030) except placeholders may be wired partially earlier for iterative feedback.
- Polish tasks (T047–T056) depend on core + integration completion.

## Parallel Execution Examples
```
# Example 1: Run initial integration test scaffolds together after T001–T008:
Task: T009, T010, T011, T012, T013, T014, T015, T016, T017, T018

# Example 2: After core services (T019–T030) done, parallelize unit tests:
Task: T047, T048, T049, T050
```

## Validation Checklist
- [ ] All FRs mapped to at least one task
- [ ] Tests precede implementations they validate
- [ ] [P] only on independent files
- [ ] No overlapping modifications in parallel tasks
- [ ] Migration atomicity & backup warning represented (T022, T027, T030)
- [ ] Secrets handling tasks present (T024, T045)

## FR Mapping Quick Reference (Sampling)
- FR-001: T031, T036
- FR-002: T019
- FR-003: T020, T025
- FR-004: T020, T022
- FR-005: T022
- FR-006: T025, T035
- FR-007: T023, T032
- FR-008: T024, T032
- FR-009: T021, T033
- FR-010: T021, T033
- FR-011: T024
- FR-012: T026, T034, T039
- FR-013: T037
- FR-014: T019
- FR-015: T021, T033, T040
- FR-016: T025, T038, T044
- FR-017: T026, T039
- FR-018: T028, T042
- FR-019: T025
- FR-020: T025
- FR-021: T019, T043
- FR-022: T030
- FR-023: T030
- FR-024: T024, T045
- FR-025: T026, T027, T041
- FR-026: T026
- FR-027: T029, T046
- FR-028: T022
- FR-029: (Implicit in T019 load-once design) documented in tests T009/T016
- FR-030: T022, T027
