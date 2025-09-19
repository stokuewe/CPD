# Feature Specification: Milestone M1: Basic GUI, Startup, and Database Connection

**Feature Branch**: `[001-milestone-m1-basic]`
**Created**: 2025-09-19
**Status**: Draft
**Input**: User description: "Establish the foundational structure for the application, including the GUI framework, project selection/creation flow, database connectivity (SQLite and optional MSSQL), and logging. Users can start working with a project safely, with clear feedback and robust version control."

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## User Scenarios & Testing (mandatory)

### Primary User Story
As a user, I want to launch the application, choose an existing project or create a new one, and receive clear feedback about the database schema and connectivity so I can start working safely.

### Acceptance Scenarios
1. Given the app has been launched, When the startup view loads, Then I see a list of recent projects and options to open an existing project or create a new project.
2. Given I select an existing .sqlite project file, When the app reads the schema version, Then it verifies compatibility and either opens the project or performs a migration with visible progress in the log view.
3. Given a schema requires migration, When migration completes successfully, Then the project opens and a success message is visible in the log; If migration fails, Then I see a clear error and the project does not open.
4. Given I choose to create a new project, When I select the storage mode (Local SQLite or MSSQL-backed) and pick a save location, Then the app initializes the project and logs the outcome.
5. Given I choose MSSQL-backed storage, When I enter connection parameters and click Test Connection, Then the app validates the connection and only proceeds to create the project if the connection test passes; otherwise I get a descriptive error.
6. Given I have opened or created a project successfully, When I return to the startup view in a subsequent session, Then the recent projects list includes that project.
7. Given I want to manage the recent projects list, When I choose Clear Recent, Then the list is emptied and the change persists.

### Edge Cases
- Opening a corrupt or non-conforming SQLite file → Error message; project not loaded.
- Missing or unreadable recent_projects.json → App recreates or ignores with warning; continues to function.
- MSSQL server unreachable or credentials invalid → Test Connection fails with actionable error; project creation blocked until resolved.
- Migration interrupted (app crash or power loss) → Before migrations, a pre-migration backup is created; on next launch a recovery marker is detected in project metadata and the user chooses: Resume migration, Restore from backup, or Cancel; the project remains unopened until a choice is made.
- Excessively long recent list or duplicate entries → The app de-duplicates entries, moves existing entries to the top on re-open, drops missing files on load, and caps the list to 10 entries.

## Requirements (mandatory)

### Functional Requirements
- FR-001: The application MUST display, at startup, a list of recently opened projects and options to Open or Create a project.
- FR-002: The application MUST persist a list of recent projects in a local JSON file (recent_projects.json) and update it after successful open/create.
- FR-003: The application MUST allow selecting an existing .sqlite file and validate its schema version before opening.
- FR-004: The application MUST perform schema migrations when the existing schema version is older than the current supported version and log migration progress.
- FR-005: If migration cannot be performed safely, the application MUST not open the project and MUST present a clear error message with remediation guidance.
- FR-006: The application MUST allow creating a new project and selecting storage mode: Local SQLite (default) or MSSQL-backed.
- FR-007: For MSSQL-backed projects, the application MUST collect server, database, port (optional), authentication type, and credentials if required.
- FR-008: For MSSQL-backed projects, the application MUST provide a Test Connection action and MUST block creation if the test fails; errors MUST be shown with actionable details.
- FR-009: The project settings, including selected storage mode and any connection descriptor, MUST be stored in the project’s local settings database file.
- FR-010: The application MUST provide a log view/window where key actions (open/create, version checks, migrations, connection tests, errors) are visible in real time.
- FR-011: The application MUST differentiate error-level messages from informational messages (e.g., visual emphasis) to alert users.
- FR-012: The application MUST allow clearing the recent projects list via the GUI and persist the change.
- FR-013: On subsequent launches, the application MUST load and render the recent projects list from storage.
- FR-014: The application MUST prevent project loading when schema compatibility checks fail and present a clear explanation.
- FR-015: The application MUST record the absolute path of the local settings database in the recent projects list.
- FR-016: The application MUST ensure all database operations required for M1 occur without blocking the UI; show a busy indicator if an operation exceeds 200 ms, and show a progress dialog (with cancel where safe) for tasks exceeding 1 s.
- FR-017: The application MUST cap the recent projects list to 10 entries and remove duplicates; re-opening an existing entry moves it to the top.
- FR-018: The application MUST maintain an audit trail in the in-GUI log for the current session; it MAY also write an optional daily-rotated log file in the user-scope application data directory.

- FR-019: System MUST authenticate MSSQL connections using either SQL Authentication or Windows Authentication per user selection.
- FR-020: System MUST redact sensitive fields (passwords) from error messages and logs.

### Key Entities (include if feature involves data)
- Project: A unit identified by a local settings database file; contains mode (sqlite/mssql), schema version, and optional connection descriptor.
- Recent Project Entry: A record containing absolute path and timestamp of last open; used for the startup list.
- Connection Descriptor: A set of fields required to test/connect to MSSQL for Remote Mode creation.

## Confirmed Defaults and Policies (M1)

- Recent projects
  - Location: user-scope application data directory
  - Entry content: project path and last-opened timestamp
  - De-duplication: remove duplicates; on add, move existing entry to top; cap to 10
  - Validation on load: drop entries whose file no longer exists
  - Clear Recent: clears the list

- Migration and recovery
  - Each migration is transactional and durable
  - Pre-migration backup: create a backup alongside the database before migrating
  - Crash/interrupt handling: detect a recovery marker in project metadata; options: Resume, Restore from backup, Cancel; do not open until resolved
  - Newer-than-supported schema: refuse to open with message to upgrade CPD

- UI responsiveness and progress
  - Show busy indicator if an operation exceeds 200 ms; show a progress dialog (with cancel where safe) for tasks >1 s; UI remains responsive

- Logging
  - In-GUI log with INFO/WARN/ERROR and color emphasis
  - Optional daily-rotated log file in the application data directory
  - Secrets redacted; never log passwords or full connection strings

- MSSQL authentication and connection
  - Support SQL Authentication and Windows Authentication
  - Defaults: secure connections enabled; uses the default port unless overridden; reasonable connection timeout; developer override available for certificate trust with explicit consent
  - Passwords are not saved in M1; prompt on each connect

- Remote Mode unavailable
  - If the MSSQL server is unreachable, block project open with actionable error; no degraded read-only mode in M1

- Schema versioning
  - Initial schema version: 1.0.0
  - Older-than-supported: run sequential migrations; newer-than-supported: refuse to open and ask to upgrade the app

- Recent path normalization
  - Normalize to absolute project paths; de-duplicate consistently; support local and network paths; store the path verbatim for display

- Settings stored in SQLite
  - Stores core project settings (e.g., name, storage mode, lifecycle timestamps)
  - For Remote Mode, stores connection details excluding passwords

- Error messaging style
  - Include problem summary, probable cause, and remediation steps (e.g., "MSSQL connection failed (timeout 5 s). Check server/instance name or VPN. You can enable 'Trust server certificate' for dev servers").

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---
