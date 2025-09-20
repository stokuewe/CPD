# Tasks: Milestone M2.1 — CRUD Editor for Canonical Standards

**Input**: Design documents from `/specs/002-milestone-m2.1-crud/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model/service tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup/validation tasks
   → quickstart.md: Extract scenarios → integration tests
3. Generate tasks by category with TDD order and [P] rules
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Phase 3.1: Setup
- [ ] T001 Create GUI/editor scaffolding folders if missing (no code yet) in `src/app/controllers/` and `src/app/dialogs/`
- [ ] T002 [P] Add placeholder module for service in `src/services/canonical_service.py` (class `CanonicalService` skeleton, no logic)
- [ ] T003 [P] Add test package init files if needed in `tests/contract/` and `tests/integration/`

## Phase 3.2: Tests First (TDD) — MUST FAIL BEFORE 3.3
- [ ] T004 [P] Contract tests for service interface in `tests/contract/test_canonical_service_contract.py` (asserts method signatures, error taxonomy, validation behavior)
- [ ] T005 [P] Integration test: open editor empty state in `tests/integration/test_canonical_editor_empty.py` (drives service layer only; asserts empty lists and guidance copy availability)
- [ ] T006 [P] Integration test: Pset + Attribute CRUD in `tests/integration/test_canonical_crud_flow.py` (create pset, add attribute, edit, delete; verifies persistence in SQLite memory or temp DB)
- [ ] T007 [P] Integration test: Value domain item management in `tests/integration/test_value_domain_items.py` (add/rename/remove; prevent duplicates case-insensitive)
- [ ] T008 [P] Integration test: Duplicate prevention and deletion safeguards in `tests/integration/test_conflicts_and_guards.py` (duplicate names; block delete when referenced in map_ifc_*)
- [ ] T009 [P] Performance test: dataset ~500/5000 in `tests/integration/test_canonical_performance.py` (open ≤1.5s; expand ≤150ms; CRUD median ≤200ms; search ≤150ms)

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T010 [P] Implement validation helpers (normalize, case-insensitive compare, allowed datatypes) in `src/lib/validation.py`
- [ ] T011 Implement `CanonicalService` data access (SQLite) in `src/services/canonical_service.py` (parameterized SQL, explicit transactions; list/create/update/delete for psets/attributes; unit and value domain references)
- [ ] T012 Add MSSQL support paths in `src/services/canonical_service.py` using `src/services/mssql_connection.py` (same semantics; no dual-write; parity guaranteed)
- [ ] T013 Implement value domain item operations in `src/services/canonical_service.py` (list/create/rename/delete; enforce duplicate-prevention per domain)
- [ ] T014 Implement deletion safeguards (check map_ifc_* references) in `src/services/canonical_service.py` for psets/attributes
- [ ] T015 Integrate structured logging using `src/services/logging_model.py` (log op, backend, target, duration_ms, row_count, status)
- [ ] T016 [P] Create Canonical Editor controller in `src/app/controllers/canonical_editor_controller.py` (connects QThread/QThreadPool to service; emits GUI signals per contracts file)
- [ ] T017 [P] Create Canonical Editor dialog/widget in `src/app/dialogs/canonical_editor_dialog.py` (list/tree of psets/attributes; side panel for metadata and value domain items; non-blocking UI)
- [ ] T018 Wire editor into main window (menu/action + handler) in `src/app/main_window.py` (open dialog; ensure thread-safety via signals/slots)

## Phase 3.4: Integration
- [ ] T019 Detect active backend (SQLite vs MSSQL) from current project context in `src/services/canonical_service.py` (reuse project loader/connection state)
- [ ] T020 Ensure foreign key and transaction settings applied per constitution (SQLite PRAGMAs; transactions around write ops) in service implementation
- [ ] T021 Add search/filter support and lazy-loading of attributes by expanded Pset in controller/dialog (performance)
- [ ] T022 Finalize error mapping to user-facing messages (ValidationError, Conflict, NotFound, StorageError) and ensure UI feedback

## Phase 3.5: Polish
- [ ] T023 [P] Unit tests for validation helpers in `tests/unit/test_validation_helpers.py`
- [ ] T024 [P] Unit tests for logging integration in `tests/unit/test_canonical_logging.py`
- [ ] T025 Update docs: add editor section to `docs/quickstart-m1.md` or new `docs/quickstart-m2.md` outlining canonical editor usage
- [ ] T026 [P] Non-interactive UI smoke: instantiate dialog and ensure it shows/hides without blocking in `tests/integration/test_canonical_editor_smoke.py`
- [ ] T027 Review constitution compliance checklist; adjust code/comments if needed

## Dependencies
- Setup (T001-T003) → Tests (T004-T009) → Core (T010-T018) → Integration (T019-T022) → Polish (T023-T027)
- T010 before T011-T014 (validators used by service)
- T011 before T012, T013, T014, T015
- T016 and T017 can proceed in parallel after T011-T015
- T018 after T016-T017

## Parallel Execution Examples
```
# Group [P] tasks that touch different files:
- T004, T005, T006, T007, T008, T009 (tests in separate files)
- T010, T016, T017 (lib vs controllers vs dialogs)
- T023, T024, T026 (unit/integration tests in separate files)
```

## Notes
- Tests must be executed with `pytest -q` on Windows; GUI tests are non-interactive (no event loop blocking)
- All SQL must be parameterized; no schema changes are allowed; behavior must match sqlite.sql and azure.sql
- Use QThread/QThreadPool for DB IO; never block the GUI thread
- Ensure identical semantics across SQLite and MSSQL backends

