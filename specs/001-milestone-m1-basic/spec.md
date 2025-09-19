# Feature Specification: Milestone M1 – Basic GUI, Startup, and Database Connection

**Feature Branch**: `001-milestone-m1-basic`  
**Created**: 2025-09-19  
**Status**: Draft  
**Input**: User description: "Milestone M1: Basic GUI, Startup, and Database Connection"

## Execution Flow (main)
```
1. Parse user description from Input
	→ If empty: ERROR "No feature description provided"
2. Extract key concepts: startup flow, recent projects list, project creation, project opening, schema versioning, migrations, logging window, dual storage mode (SQLite or MSSQL), recent_projects persistence.
3. Identify unclear aspects → mark with [NEEDS CLARIFICATION]
4. Draft User Scenarios & Acceptance Scenarios from provided journey.
5. Generate Functional Requirements (testable, implementation-agnostic).
6. Identify Key Entities: Project, RecentProjectEntry, SchemaVersion, Migration, StorageMode, MSSQLConnectionProfile, LogEntry.
7. Review for implementation leakage (e.g., avoid naming specific libraries beyond what is mandated by constitution scope) – retain business-level framing.
8. If any [NEEDS CLARIFICATION] remain → WARN "Spec has uncertainties".
9. Output specification document (this file) for review.
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW (no detailed class diagrams, no low-level API calls)
- 👥 Audience: stakeholders & product reviewers

### Section Requirements
- Mandatory sections filled; optional sections included only if relevant.
- Ambiguities flagged explicitly.

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a user starting the application, I want to open or create a project and immediately see clear feedback about database status (schema validity, migrations) so I can confidently begin work without risking data corruption or version incompatibility.

### Supporting User Stories
1. As a user, I want to quickly re-open recently used projects from a list so I do not have to browse for them each time.
2. As a user creating a project, I want to choose whether all data stays local or large domain data lives in a remote MSSQL database so I can balance simplicity vs scalability.
3. As a user choosing MSSQL, I want to test the connection before committing so I avoid creating an unusable project configuration.
4. As a user opening an existing project, I want automatic safe migrations (or a clear refusal) so my project remains compatible.
5. As a user, I want a live log window that shows operations and errors distinctly so I can understand what the system is doing and react to failures.
6. As a user, I want to clear the recent projects list to remove obsolete or sensitive paths.

### Acceptance Scenarios
1. Given application launch with no prior projects, When GUI loads, Then the Recent Projects list is empty and options to Open or Create are presented.
2. Given a valid existing project file at schema version current, When user selects Open, Then project loads, schema is validated, and a success message appears in the log window.
3. Given a project file with outdated but migratable schema, When user opens it, Then the user is shown a warning advising them to backup the file before proceeding, migrations then run sequentially with each step logged, and the project loads upon success.
4. Given a corrupt or incompatible project file, When user attempts to open it, Then an error message is shown, the project is not loaded, and the recent projects list is not updated with a failed attempt.
5. Given user chooses Create Project (local mode), When they provide a file path and confirm, Then a new project file is created with initial schema, meta entry for schema_version, and success logged.
6. Given user chooses Create Project (remote mode), When they enter MSSQL parameters and click Test Connection with valid credentials, Then success is logged and they can finalize project creation.
7. Given user chooses remote mode and Test Connection fails, When they attempt to create project, Then creation is blocked and an error is logged.
8. Given user opens or creates a project successfully, When operation completes, Then that project path appears at top of Recent Projects list persisted to disk.
9. Given user opens Recent Projects menu, When they choose Clear List, Then recent_projects.json is emptied and GUI list reflects change.
10. Given GUI is running, When any logged error occurs, Then it is visually differentiated (e.g., icon/prefix/color) from non-error entries.

### Edge Cases
- Opening a file that is not a valid SQLite database → Show validation error, do not modify recent list. 
- Opening a database missing required meta keys → Treat as incompatible; instruct user to migrate manually or recreate.
- Migration script partially succeeds then fails → Rollback (where feasible) and present failure summary; project not loaded.
- Recent projects file unreadable/corrupt → Regenerate a fresh empty list and log a warning (not fatal).
- Duplicate project path added → Ensure list de-duplicates while reordering to most-recent.
- MSSQL connection slow or times out → Provide timeout-specific error and allow retry without losing form inputs.
- User cancels project creation mid-process → No partial artifacts left (no half-created DB file with missing tables).
- Attempt to open a project created with a newer future schema version → Block with message instructing upgrade of application.
- MSSQL selected but driver/connection layer unavailable → Block remote mode creation; suggest installing prerequisites.

---

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST present a startup screen listing recent projects and offering options to open an existing project or create a new one.
- **FR-002**: System MUST persist recent project entries in a local `recent_projects.json` file updated only after successful open/create operations.
- **FR-003**: System MUST allow opening a user-selected `.sqlite` file and validate it as a project database before loading.
- **FR-004**: System MUST read and evaluate the stored schema version and determine if migration is required, disallowed, or unnecessary.
- **FR-005**: System MUST execute required migration steps in deterministic order and log each step with outcome.
- **FR-006**: System MUST block project load if migrations fail or the version is incompatible, presenting a clear user-facing error summary.
- **FR-007**: System MUST allow creation of a new project with a chosen file path and initialize required meta/settings tables and baseline schema entries.
- **FR-008**: System MUST offer a storage mode choice: `sqlite` (all data local) or `mssql` (project data remote; settings local) during project creation.
- **FR-009**: System MUST, when `mssql` mode is chosen, display a form for connection parameters and provide a "Test Connection" action producing success/failure feedback.
- **FR-010**: System MUST prevent finalizing project creation in `mssql` mode until a successful connection test occurs in the same session.
- **FR-011**: System MUST store MSSQL connection parameters (excluding sensitive secrets in plain text) in the local project settings area when remote mode is selected.
- **FR-012**: System MUST differentiate log severity levels visually in the log window (info, warning, error at minimum).
- **FR-013**: System MUST allow users to clear the entire recent projects list via a user action requiring confirmation.
- **FR-014**: System MUST de-duplicate recent project entries, moving an existing one to the top when re-opened.
- **FR-015**: System MUST handle and report connection timeouts distinctly from authentication failures for MSSQL tests.
- **FR-016**: System MUST mark a project as read-only (and refuse writes) if opened in remote mode but the MSSQL server is unreachable at open time.
- **FR-017**: System MUST log both success and failure of each major operation (open, create, migrate, test connection, clear recent list).
- **FR-018**: System MUST ensure partial project creation artifacts are removed if creation is aborted or fails before initialization completes.
- **FR-019**: System MUST reject opening databases created by a newer application schema version, instructing user to update the application.
- **FR-020**: System MUST validate that required meta keys (e.g., `schema_version`) exist; missing keys trigger an incompatibility error.
- **FR-021**: System MUST impose an upper bound on the number of stored recent project entries (e.g., 15) and drop oldest beyond the limit.
- **FR-022**: System MUST produce a structured in-memory representation of current project state (path, mode, version) for potential context capsule usage.
- **FR-023**: System MUST allow launching without any valid recent projects present (graceful empty state).
- **FR-024**: System MUST ensure that sensitive credentials for MSSQL are not written to plain-text logs.
- **FR-025**: System MUST provide actionable remediation text on errors (e.g., migration failure suggests verifying file permissions or backup restore).
- **FR-026**: System MUST provide a confirmation message in the log window after successful project load or creation.
- **FR-027**: System MUST prevent simultaneous duplicate migration execution (e.g., double-open click) via operation locking.
- **FR-028**: System MUST version-control migrations such that each applied migration is recorded exactly once for that project.
- **FR-029**: System MUST load the recent projects list only once at startup; no manual refresh action or auto-reload beyond initial load is included in this milestone.
- **FR-030**: System MUST perform migrations atomically with no mid-migration cancellation; before executing required migrations the user MUST be shown a warning advising creation of a backup.

### Key Entities
- **Project**: Represents a logical working environment defined by a settings SQLite file path and storage mode; includes schema version and mode flag.
- **RecentProjectEntry**: A record of a previously successful open/create action with absolute path and timestamp.
- **SchemaVersion**: The semantic version identifier stored in meta; determines required migrations.
- **Migration**: A versioned transformation that brings a project database from one schema state to the next.
- **StorageMode**: Enumeration-like concept: `sqlite` or `mssql` specifying where domain data resides.
- **MSSQLConnectionProfile**: Parameters necessary to connect to remote database (server, database name, optional port, auth type, optional username, secret reference).
- **LogEntry**: A severity-tagged message reflecting an operational event (info/warn/error) shown in real time.

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs) beyond mandated architectural context
- [x] Focused on user value and observable behavior
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements testable & unambiguous
- [x] Success criteria measurable (pass/fail per scenario)
- [x] Scope clearly bounded (startup, project open/create, logging, migrations, storage mode choice only)
- [x] Dependencies & assumptions identified (SQLite base, optional MSSQL availability, migration scripts exist)

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities resolved (FR-029, FR-030)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed (awaiting stakeholder approval sign-off)

---

