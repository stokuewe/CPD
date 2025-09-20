# Implementation Plan: Milestone M2.1 — CRUD Editor for Canonical Standards

**Branch**: `002-milestone-m2-1` | **Date**: 2025-09-20 | **Spec**: specs/002-milestone-m2.1-crud/spec.md
**Input**: Feature specification from `specs/002-milestone-m2.1-crud/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands.

## Summary
Primary requirement: Provide a PySide6 GUI editor to create/read/update/delete canonical Psets and Attributes (with datatype, optional unit, optional value domain), manage value domain entries, log all actions, and persist changes to the project database. No schema changes.

High-level approach: Implement a non-blocking PySide6 editor that operates on existing canonical_* tables through the existing storage gateway(s), enforcing uniqueness and validations at the application layer, and emitting structured logs. Maintain responsiveness within the specified performance budgets.

## Technical Context
**Language/Version**: Python 3.13 (Windows)
**Primary Dependencies**: PySide6 (GUI), stdlib sqlite3 (SQLite), pyodbc (MSSQL via ODBC), IfcOpenShell (project-wide, not central to this feature)
**Storage**: SQLite (local settings + optional project data) and MSSQL (remote mode project data) via explicit SQL with parameterized queries; no schema changes
**Testing**: pytest; non-interactive UI smoke tests where feasible
**Target Platform**: Windows 10/11 desktop (GUI-first)
**Project Type**: single (desktop app + services)
**Performance Goals**: Open editor ≤ 1.5 s; expand Pset ≤ 150 ms; add/edit/delete ≤ 200 ms median; search/filter ≤ 150 ms
**Constraints**: GUI thread unblocked; writes in explicit transactions; PRAGMA foreign_keys=ON; WAL preferred; parameterized SQL only; no schema changes; parity between SQLite and MSSQL; logging redacts secrets
**Scale/Scope**: ~500 Psets, ~5,000 Attributes; no pagination in M2.1; undo/redo out of scope

## Constitution Check
Gate assertions (PASS unless noted):
- Windows + Python 3.13 only: PASS (desktop PySide6)
- PySide6 GUI-first; long ops off main thread: PASS (use QThread/QThreadPool for DB IO)
- User-managed SQLite; migrations only via user_version; explicit transactions; WAL: PASS (no schema changes; parameterized queries)
- Optional MSSQL remote mode; schema parity; no dual-write: PASS (use StorageGateway abstraction; identical semantics)
- IFC via IfcOpenShell maintained: N/A to this feature (no direct IFC processing)
- AI/session memory constraints unchanged: PASS
- Security/privacy: PASS (no new secret handling; redact logs)

No violations identified; Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)
```
specs/002-milestone-m2.1-crud/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: DEFAULT to Option 1 (single project). No web/mobile split introduced.

## Phase 0: Outline & Research
See research.md (generated) – unknowns validated against spec; decisions recorded with rationale; no open NEEDS CLARIFICATION remain for M2.1.

## Phase 1: Design & Contracts
Outputs generated:
- data-model.md (entities/fields/relationships aligned to sqlite.sql and azure.sql)
- contracts/service-contracts.md (service interfaces + GUI interactions; no web API introduced)
- quickstart.md (scenario-driven validation steps and performance checks)

Agent context update: deferred until tasks are generated and plan is committed on an appropriate feature branch.

## Phase 2: Task Planning Approach (DO NOT EXECUTE IN /plan)
- Load `.specify/templates/tasks-template.md` as base in /tasks
- Derive tasks from: contracts, data model, quickstart scenarios
- TDD order (tests first), dependencies (models → services → UI)
- Mark independent contract tests as [P] for parallel execution

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|

## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
Based on Constitution v1.1.0 - See `.specify/memory/constitution.md`
