<!--
Sync Impact Report
- Version: N/A → 1.1.0
- Modified principles: Core Principles populated (I–V)
- Added sections:
  • Section 2: Dual Storage Architecture (SQLite Settings + Optional MS SQL Project Data)
  • Section 3: Technology & Constraints; Development Workflow; Storage & Migration Model; Error Handling & Observability; Security & Privacy; Versioning & Compliance; Appendices; Acceptance (summarized)
- Templates requiring updates:
  • .specify/templates/plan-template.md: ✅ footer updated to v1.1.0 and correct path
  • .specify/templates/spec-template.md: ✅ no change needed
  • .specify/templates/tasks-template.md: ✅ no change needed
- Follow-up TODOs: none
-->

# CPD Constitution

## Core Principles

### I. Windows + Python 3.13 Only
The application targets Windows 10/11 exclusively and runs on Python 3.13. No cross‑platform
shims/conditionals or unsupported interpreters. Default encoding is UTF‑8; use Windows‑safe path APIs.
Dependencies are version‑pinned for deterministic builds and reproducible debugging.

### II. PySide6 GUI‑First
All user interactions occur via a PySide6 desktop UI. The GUI thread stays unblocked. Long‑running or
blocking operations (DB IO, IFC parsing, network/MSSQL) use QThread/QThreadPool or async Qt
patterns with signals/slots. A minimal optional CLI MAY exist but MUST NOT complicate or fragment the
GUI code path.

### III. User‑Managed SQLite (Settings & Local Mode)
User selects/creates the primary settings/database file (.sqlite). On first open, initialize schema;
thereafter migrate via incremental SQL keyed by PRAGMA user_version. Always enforce:
- PRAGMA foreign_keys = ON
- Prefer PRAGMA journal_mode = WAL
- Prefer PRAGMA synchronous = NORMAL
All writes are inside explicit transactions. Never silently relocate/duplicate this file. The absolute
path is always user‑visible. This file stores: application settings, connection profiles, context
capsule, migration metadata, ADR index, and (in pure‑local mode) all project data.

### IV. IFC via IfcOpenShell
Use IfcOpenShell for reading/writing BuildingSMART IFC (IFC2x3 & IFC4). Maintain stable mapping
between internal records and IFC GlobalId + ifc_type. Avoid heavy geometry unless explicitly
requested; gate geometry behind capability checks. Validate IFC schema compatibility on load and
present clear diagnostics upon mismatch/corruption. Preserve referential consistency between DB rows
and IFC entities.

### V. AI‑Friendly & Session Memory
Design for small‑context LLM collaboration. Maintain a compact rotating context capsule (≤ 3 KB)
containing: open DB path, storage mode, schema version, pending migrations, active IFC file, selected
entity IDs, and current task summary. Persist at `.specify/memory/context-capsule.json`. Capture
concise ADRs under `.specify/adr/`. Prompts/specifications live under `.specify/`. Prefer deterministic,
text‑first logs, metadata exports, and machine‑diffable outputs.

## Dual Storage Architecture (SQLite Settings + Optional MS SQL Project Data)
Project settings ALWAYS reside in the local SQLite settings DB. Project data MAY live either in the
same SQLite file (Local Mode) or in a Microsoft SQL Server database (Remote Mode) chosen during
project creation/migration. Never persist the same project data concurrently in both backends. Remote
Mode stores only project domain tables in MSSQL; local SQLite continues to store settings, connection
descriptors, a unified schema ledger (covering both dialects), and minimal sync metadata.
Rules:
- Mode is immutable per project unless an explicit, user‑approved migration tool performs a one‑way
  copy (with dry run & report). Migration MUST be explicit and logged.
- Credentials stored encrypted (Windows DPAPI or credential vault) or via named ODBC DSN; never in
  plain‑text logs.
- All DB access uses parameterized queries; prohibit SQL string concatenation except static DDL.
- Schema parity: logical model is uniform; dialect‑specific DDL kept in paired migration scripts
  (migrations/sqlite/NNNN.sql and migrations/mssql/NNNN.sql). A migration is considered applied only
  when recorded in the local settings DB with backend & timestamp.
- Failure isolation: if MSSQL is unreachable, open project in read‑only degraded mode (no writes) with
  clear UI status. No silent write queueing.
- Observability: MSSQL operations include timing, affected row count, and retry outcomes in structured
  logs.
- No implicit fallback from MSSQL to SQLite for the same project once Remote Mode is established.
- Consistency: multi‑step domain operations use explicit transactions (BEGIN/COMMIT/ROLLBACK) in
  MSSQL. Cross‑backend distributed transactions are forbidden.
- Testing MUST include: connection failure handling, migration divergence detection, latency impact
  (simulated), and correctness of fallback to read‑only.
Rationale: MSSQL option allows scaling project data volume and concurrency while retaining
user‑owned local configuration and offline introspection.

## Technology, Workflow, and Compliance Overview
- Runtime & Tech Constraints:
  • Python 3.13 (Windows). Public APIs typed. stdlib logging (plain/JSON). Avoid global mutable state
    except controlled singletons (e.g., AppContext).
  • GUI: PySide6 only. UI updates on main thread via signals. Use resource compilation as needed.
  • Database (Settings): stdlib sqlite3 with Row factory. One definitive settings file per user/project.
    Backups/VACUUM are user‑triggered. Schema via sequential migrations keyed by user_version.
  • Database (Project Data Remote): MSSQL via ODBC (pyodbc or vetted driver). Provide a thin
    StorageGateway abstraction with common‑subset SQL and capability flags; keep DDL explicit.
  • IFC: IfcOpenShell pinned. Support open/query/write/export; geometry optional and guarded.
  • Files & Settings: Write only within user‑chosen dirs except `.specify/` for logs/ephemera. Secrets
    never in git.
  • Security: No embedded creds. Least‑priv MSSQL roles. Redact secrets in logs. Handle UNC/long
    paths via Windows APIs.
  • Performance: WAL for SQLite concurrency; batch MSSQL writes in transactions; avoid N+1.
- Development Workflow:
  • Changes small/reviewable (Conventional Commits preferred). Merge updates context capsule; AD
    decisions produce short ADRs.
  • Migration pipeline: add paired migration files; update manifest; include tests proving forward
    migration & blank init equivalence. PRs show resulting PRAGMA user_version and MSSQL schema diff.
  • Tests focus on: SQLite/MSSQL init & migrations; downgrade rejection paths; IFC import/export
    cycle; UI non‑interactive smoke; adapter parity across backends.
  • Dependency pinning via requirements.txt (hash‑locked optional). Document install & run in README.
    Provide scripts/bootstrap.ps1.
  • Logging includes: op, backend (sqlite|mssql), target, duration, row count, outcome, and actionable
    remediation in UI on errors.
  • Review checklist: thread confinement, signal/slot correctness, migration idempotency, no duplicate
    storage, logging completeness, IFC mapping preservation.
- Storage & Migration Model:
  • Authority for mode: SQLite is source of truth; MSSQL referenced only.
  • Migrations ledger centralized in SQLite; MSSQL has no ledger—applied via scripts but recorded in
    SQLite.
  • No data duplication across backends in Remote Mode. Explicit transactions in both; offline behavior:
    SQLite full R/W; MSSQL read‑only degraded.
- Error Handling & Observability:
  • Uniform error taxonomy (StorageError, MigrationError, IFCLoadError, ValidationError).
  • User dialogs summarize failure, log ID, remediation. Logs structure: {timestamp, level, op,
    backend, target, duration_ms, row_count, status, message}.
  • Health panel shows backend, schema version(s), pending migrations, last capsule update time.
- Security & Privacy:
  • Redact passwords/tokens; privacy mode may redact paths. No telemetry without explicit opt‑in.
  • Secrets never written to ADRs or capsule.
- Versioning & Compliance:
  • Constitution versioning: MINOR for additive governance changes; MAJOR for breaking constraints;
    PATCH for clarifications. Tooling MAY include compliance scans blocking non‑compliant PRs.
- Appendices (summarized references):
  • Context Capsule Schema (≤ 3 KB target) lives at `.specify/memory/context-capsule.json`.
  • Migration File Naming: paired backend files; add no‑op counterpart when backend‑agnostic.
  • Minimal Storage Adapter Interface: thin protocol with connect/tx/query operations.
- Acceptance: By contributing, you agree to uphold this constitution. Amendments MUST follow the
  process below.

## Governance
This constitution defines non‑negotiable constraints. Amendments are required for: runtime platform
changes; GUI framework changes; database ownership or storage mode changes; IFC handling model
shifts; AI/context persistence format adjustments exceeding size/structure constraints.
Amendment PR requirements:
1. Rationale & impact summary
2. Migration & rollback (if applicable)
3. Updated context capsule example
4. Updated version + amendment date
5. Test plan adjustments
Reviews must verify strict compliance before merge. Violations discovered post‑merge trigger an
immediate corrective issue.

**Version**: 1.1.0 | **Ratified**: 2025-09-15 | **Last Amended**: 2025-09-19

