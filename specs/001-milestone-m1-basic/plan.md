# Implementation Plan: Milestone M1 – Basic GUI, Startup, and Database Connection

**Branch**: `001-milestone-m1-basic` | **Date**: 2025-09-19 | **Spec**: `spec.md`  
**Input**: Feature specification from `C:/Users/morit/Desktop/GitHub/CPD/specs/001-milestone-m1-basic/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec → success
2. Fill Technical Context
   - Extracted platform, language, storage modes, logging needs; no remaining clarifications.
3. Constitution Check (using project constitution in repo root `CONSTITUTION.md` as authoritative vs placeholder memory file)
4. Initial Constitution Check gate: PASS (no violations)
5. Phase 0 executed → research.md generated with 10 decisions
6. Phase 1 executed → data-model.md, contracts placeholder, quickstart.md generated
7. Post-Design Constitution Check → PASS (design respects constraints)
8. Phase 2 approach documented (tasks strategy) – tasks.md not created per scope
9. STOP
```

## Summary
Deliver initial application shell enabling: project creation (SQLite or MSSQL-backed), project opening with schema validation & atomic migration, logging differentiation, persistent recent project list (capped and de-duplicated), and read-only fallback for unreachable remote storage.

## Technical Context
**Language/Version**: Python 3.13 (Windows-only)  
**Primary Dependencies**: PySide6 (GUI), stdlib sqlite3, pyodbc (planned for MSSQL connectivity), IfcOpenShell (not exercised in M1)  
**Storage**: SQLite (settings & local mode), Optional MSSQL (remote project data)  
**Testing**: pytest (unit + integration smoke), potential Qt headless plugin for smoke tests  
**Target Platform**: Windows 10/11 desktop  
**Project Type**: Single desktop application (Option 1 structure)  
**Performance Goals**: Fast startup (< 2s cold start typical), migration execution atomic; log UI updates < 50ms latency  
**Constraints**: Atomic migrations, no duplicate project data across backends, GUI-thread safety, context capsule future-friendly  
**Scale/Scope**: M1 limited to foundational lifecycle; up to 15 recent entries

## Constitution Check
Validated against `CONSTITUTION.md` (v1.1.0):
- Platform restricted to Windows + Python 3.13 → Compliant
- PySide6 GUI-first approach → Compliant
- SQLite user-managed file path surfaced → Compliant
- Dual storage with optional MSSQL, no duplication → Compliant
- AI-friendly context: will later produce capsule; M1 prepping state shape only → Compliant
- No disallowed cross-platform abstractions or ORM introduction → Compliant
No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)
```
specs/001-milestone-m1-basic/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── README.md
└── (tasks.md to be added by /tasks phase)
```

### Source Code (anticipated initial layout)
```
src/
  app/                # Application bootstrap (main window, event loop)
  ui/                 # PySide6 widgets/dialogs (startup screen, log panel)
  storage/            # SQLite + MSSQL adapters (interface + concrete)
  migrations/         # Baseline and future scripts
  services/           # Project service (open/create), migration service, recent projects service
  logging/            # Logging config + GUI bridge
tests/
  unit/
  integration/
```

**Structure Decision**: Option 1 (single project) – Desktop GUI with no separate frontend/backend split.

## Phase 0: Outline & Research (Completed)
See `research.md` (D1–D10). All earlier ambiguities resolved; no open unknowns blocking design.

## Phase 1: Design & Contracts (Completed)
- Data model defined (baseline meta/settings/mssql_connection).  
- No external service API → contracts placeholder only.  
- Quickstart defines validation flow for M1 success criteria.  
- Interfaces to be codified in code (StorageAdapter abstraction) during implementation, not exported as network API.

## Phase 2: Task Planning Approach
Will convert Functional Requirements (FR-001 .. FR-030) into tasks grouped by layers:
1. Foundation: directory scaffold, logging setup
2. Data layer: SQLite schema bootstrap, MSSQL connection probe utility
3. Services: project lifecycle, migration, recent projects persistence
4. UI: startup window, dialogs (create project, MSSQL params), log panel, error modal
5. Integration tests: open/create flows, migration simulation, read-only remote fallback
Ordering ensures lower-level stability before UI wiring. Parallelizable tasks flagged for independent work (e.g., recent projects service vs log panel).

## Phase 3+: Future Implementation
Out of scope for /plan. /tasks will enumerate actionable steps. Later phases integrate IFC + context capsule persistence.

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| (none)    |            |                                      |

## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none required)

---
*Aligned with Constitution v1.1.0*
