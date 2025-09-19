# Implementation Plan: Milestone M1: Basic GUI, Startup, and Database Connection

**Branch**: `001-milestone-m1-basic` | **Date**: 2025-09-19 | **Spec**: specs/001-milestone-m1-basic/spec.md  
**Input**: Feature specification from `/specs/001-milestone-m1-basic/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
2. Fill Technical Context
3. Fill Constitution Check section
4. Evaluate Constitution Check
5. Execute Phase 0 → research.md
6. Execute Phase 1 → contracts/, data-model.md, quickstart.md
7. Re-evaluate Constitution Check
8. Plan Phase 2 → Describe task generation approach (no tasks.md yet)
9. STOP - Ready for /tasks command
```

## Summary
Milestone M1 delivers a Windows desktop application foundation where users can launch the app, open an existing project or create a new one, and receive clear feedback about database schema checks/migrations and (optional) MSSQL connectivity. A GUI log and recent projects list provide transparency and convenience.

## Technical Context
**Language/Version**: Python 3.13  
**Primary Dependencies**: PySide6 (GUI), built-in sqlite (settings/local projects), pyodbc (MSSQL connectivity)  
**Storage**: Local SQLite settings DB (always); project data in SQLite (Local Mode) or SQL Server (Remote Mode)  
**Testing**: pytest, pytest-qt (QtBot)  
**Target Platform**: Windows 10/11 desktop  
**Project Type**: single (desktop app)  
**Performance Goals**: Responsive UI; show busy indicator >200 ms; progress dialog >1 s (cancel where safe)  
**Constraints**: No schema changes; all logic must conform to sqlite.sql and azure.sql; redact secrets; Windows-only; GUI-first  
**Scale/Scope**: Single-user desktop; typical recent list size ≤ 10 entries

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Windows + Python 3.13 only → Plan targets Windows 10/11 and Python 3.13 (PASS)
- GUI-first with PySide6 → Plan centers on a PySide6 desktop GUI (PASS)
- User-managed SQLite settings; optional SQL Server project data → Plan stores settings locally; supports Remote Mode via MSSQL (PASS)
- Schema synchronization rule → Plan makes no schema changes; strictly conforms to sqlite.sql and azure.sql (PASS)
- Security & privacy basics → Plan redacts secrets and avoids password storage in M1 (PASS)
- AI-friendly and session memory → Plan aligns with context-capsule and logging guidance (PASS)

Post-Design Check: Re-validated after Phase 1 — no violations introduced (PASS)

## Project Structure

### Documentation (this feature)
```
specs/001-milestone-m1-basic/
├── plan.md              # This file (/plan output)
├── research.md          # Phase 0 output (/plan)
├── data-model.md        # Phase 1 output (/plan)
├── quickstart.md        # Phase 1 output (/plan)
├── contracts/           # Phase 1 output (/plan)
└── tasks.md             # Phase 2 output (/tasks - NOT created by /plan)
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

**Structure Decision**: DEFAULT to Option 1 (single desktop app project)

## Phase 0: Outline & Research
1) Extracted unknowns from spec → finalized defaults in spec (recent list cap, responsiveness, logging, migration recovery, MSSQL connection policy).  
2) Research tasks and outcomes captured in research.md, including rationale and alternatives considered (e.g., password storage deferred past M1; no degraded read-only mode in M1).

Output: research.md complete (see file in this directory)

## Phase 1: Design & Contracts
1) Entities extracted to data-model.md: Project Settings, Recent Project Entry, Connection Descriptor (Remote Mode). Includes validation and constraints aligned with sqlite.sql and azure.sql (no schema changes).  
2) GUI Interaction Contracts created under contracts/: startup view, open project, create project, test connection, logging.  
3) Quickstart.md summarizes validation and smoke steps aligned with acceptance scenarios.

Outputs: data-model.md, contracts/*, quickstart.md generated

## Phase 2: Task Planning Approach
This plan does NOT generate tasks.md. The /tasks command will:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each user action contract → integration test task
- Entities → model/service scaffolding tasks
- Implementation tasks to make tests pass
- Ordering: TDD (tests before implementation); dependency order (models → services → UI)

## Complexity Tracking
No constitutional violations requiring justification.

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
*Based on Constitution v1.1.0 - See `.specify/memory/constitution.md`*
