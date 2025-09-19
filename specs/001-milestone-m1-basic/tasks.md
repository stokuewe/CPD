# Tasks: Milestone M1: Basic GUI, Startup, and Database Connection

**Input**: Design documents from `/specs/001-milestone-m1-basic/`  
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Format: `[ID] [P?] Description`
- [P]: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Phase 3.1: Setup
- [x] T001 Create source tree and test layout in repository root: `src/`, `tests/unit/`, `tests/integration/`, `tests/contract/`
- [x] T002 Create Python project scaffolding and configuration files: `pyproject.toml` (or `requirements.txt` + `pytest.ini`) with entries for PySide6, pytest, pytest-qt, pyodbc (do not install packages yet)
- [x] T003 [P] Add Windows CI placeholder workflow `/.github/workflows/ci.yml` (lint + tests on Windows) [skeleton only]
- [x] T004 Add utility module for paths `src/lib/paths.py` that resolves the user-scope application data directory and recent list path (implementation TBD per plan)
- [x] T005 Add logging redaction utilities `src/lib/redaction.py` for scrubbing secrets from messages (passwords, connection strings)

## Phase 3.2: Tests First (TDD) — MUST COMPLETE BEFORE 3.3
- [x] T006 [P] Contract test for Startup View behavior in `tests/integration/test_startup_view.py` (loads recent list, shows actions)
- [x] T007 [P] Contract test for Open Existing Project in `tests/integration/test_open_project_sqlite.py` (schema check, migrate on outdated, refuse on newer)
- [x] T008 [P] Contract test for Create New Project (Local Mode) in `tests/integration/test_create_project_local.py`
- [x] T009 [P] Contract test for Create New Project (Remote Mode) + Test Connection in `tests/integration/test_create_project_remote.py`
- [x] T010 [P] Contract test for Clear Recent in `tests/integration/test_clear_recent.py`
- [x] T011 [P] Unit tests for Recent Projects service in `tests/unit/test_recent_projects.py` (cap=10, de-dup, move-to-top, drop missing, persist)
- [x] T012 [P] Unit tests for logging redaction in `tests/unit/test_redaction.py`
- [x] T013 [P] Unit tests for MSSQL connection tester error mapping in `tests/unit/test_mssql_connection.py` (timeouts, auth failure, cert trust override message)
- [x] T014 [P] Unit tests for migration runner control flow in `tests/unit/test_migrations.py` (transactional, pre-migration backup recorded, recovery marker handling)

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [x] T015 Implement Recent Projects service `src/services/recent_projects.py` (read/write list, normalization, cap=10, de-dup, move-to-top)
- [x] T016 Implement Logging Model + sink `src/services/logging_model.py` (in-GUI log levels INFO/WARN/ERROR, redaction hook to lib/redaction)
- [x] T017 Implement Project Loader `src/services/project_loader.py` (open SQLite settings DB, read schema_version, orchestrate migrations or refusal per plan)
- [x] T018 Implement Migration Runner `src/services/migration_runner.py` (transactional, pre-migration backup reference, recovery marker handling; no schema edits beyond executing approved scripts)
- [x] T019 Implement MSSQL Connection Tester `src/services/mssql_connection.py` (SQL/Windows auth, secure default, developer override flag, redact errors)
- [x] T020 Implement Project Creator (Local) `src/services/project_creator_local.py` (create new SQLite project settings DB; execute sqlite.sql to initialize; write initial metadata)
- [x] T021 Implement Project Creator (Remote) `src/services/project_creator_remote.py` (store connection descriptor excluding password; requires T019 success)
- [x] T022 Implement Path + Settings persistence `src/services/settings_store.py` (project_name, storage_mode, created_at, last_opened_at; connection details excluding passwords)

## Phase 3.4: GUI (PySide6)
- [x] T023 Create main window and startup view `src/app/main_window.py` (recent list view, Open, Create, Clear Recent, log pane)
- [x] T024 Wire actions to services `src/app/controllers/startup_controller.py` (Open → Project Loader; Create Local/Remote → creators; Clear Recent → service; log via Logging Model)
- [x] T025 Create MSSQL connection dialog `src/app/dialogs/mssql_connection_dialog.py` (fields per spec; includes Test Connection button)
- [x] T026 Ensure UI responsiveness per plan thresholds (busy indicator >200ms; progress dialog >1s with safe cancel)

## Phase 3.5: Integration
- [x] T027 Integrate sqlite.sql execution for new project setup in `src/services/project_creator_local.py` (apply schema script; no modifications to schema files)
- [x] T028 Integrate azure.sql conformance checks for Remote Mode paths in `src/services/project_creator_remote.py` (no server schema changes; validate connectivity only)
- [x] T029 Hook Logging Model to GUI log pane `src/app/main_window.py` (color emphasis by level)
- [x] T030 Update recent list after successful open/create in controllers; persist via service

## Phase 3.6: Polish
- [x] T031 [P] Unit tests for path normalization + UNC handling `tests/unit/test_paths.py`
- [x] T032 [P] Add Quickstart manual validation checklist to repository docs `docs/quickstart-m1.md` (from specs quickstart.md)
- [x] T033 [P] Documentation: Update README section for M1 usage `README.md`
- [x] T034 [P] Performance check: verify UI thresholds with artificial delays in tests (pytest-qt) `tests/integration/test_responsiveness.py`

## Dependencies
- Setup (T001–T005) before Tests and Implementation
- Tests (T006–T014) must be written and failing before Core (T015–T022)
- Core services before GUI wiring (T023–T026)
- Local/Remote creators depend on Project Loader, Migration Runner, Connection Tester as applicable
- Integration (T027–T030) after Core and GUI elements ready
- Polish (T031–T034) last; [P] tasks can run together if files differ

## Parallel Execution Examples
```
# Example 1: Launch all [P] tests in parallel after setup
Task: "Contract test Startup View" → tests/integration/test_startup_view.py
Task: "Contract test Open Project (SQLite)" → tests/integration/test_open_project_sqlite.py
Task: "Contract test Create Project (Local)" → tests/integration/test_create_project_local.py
Task: "Contract test Create Project (Remote)" → tests/integration/test_create_project_remote.py
Task: "Contract test Clear Recent" → tests/integration/test_clear_recent.py

# Example 2: Parallel unit tests
Task: "Recent Projects service unit tests" → tests/unit/test_recent_projects.py
Task: "Logging redaction unit tests" → tests/unit/test_redaction.py
Task: "MSSQL connection tester unit tests" → tests/unit/test_mssql_connection.py
Task: "Migration runner control flow unit tests" → tests/unit/test_migrations.py
```

## Validation Checklist
- [ ] All contracts have corresponding tests
- [ ] All entities have model tasks
- [ ] All tests come before implementation
- [ ] Parallel tasks truly independent
- [ ] Each task specifies exact file path
- [ ] No task modifies same file as another [P] task

