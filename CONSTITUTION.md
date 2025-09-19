# Project Constitution

**Name**: (Set during project initialization)  
**Version**: 1.1.0  
**Ratified**: 2025-09-15  
**Last Amended**: 2025-09-19  
**Amendment Summary (1.1.0)**: Introduced optional Microsoft SQL Server backend for project data while retaining mandatory local SQLite for application settings.

---
## Core Principles

### I. Windows + Python 3.13 Only
The application targets Windows 10/11 exclusively and runs on Python 3.13. No cross‑platform shims, conditionals, or unsupported interpreters. Default encoding is UTF-8; paths use Windows-safe APIs. Dependencies are version-pinned for deterministic builds and reproducible debugging.

### II. PySide6 GUI-First
All user interactions are via a PySide6 desktop UI. The main (GUI) thread stays unblocked. Long-running or blocking operations (DB IO, IFC parsing, network/MSSQL calls) use `QThread`, `QThreadPool`, or asynchronous patterns with Qt signals/slots. A minimal optional CLI MAY exist but MUST NOT complicate or fragment the GUI code path.

### III. User-Managed SQLite (Settings & Local Mode)
The user selects or creates the primary **settings/database file** (`.sqlite`). On first open, initialize schema; thereafter migrate using incremental SQL keyed by `PRAGMA user_version`. Always enforce:
- `PRAGMA foreign_keys = ON`
- Prefer `PRAGMA journal_mode = WAL`
- Prefer `PRAGMA synchronous = NORMAL`
All writes occur inside explicit transactions. Never silently relocate or duplicate this file. The absolute path is always user-visible. This file permanently stores: application settings, connection profiles, context capsule, migration metadata, ADR index, and (when in pure-local mode) all project data.

### IV. IFC via IfcOpenShell
Use IfcOpenShell for reading / writing BuildingSMART IFC (IFC2x3 & IFC4). Maintain a stable mapping between internal records and IFC `GlobalId` plus `ifc_type`. Avoid heavy geometry unless explicitly requested; gate geometry behind capability checks. Validate IFC schema compatibility on load and present clear diagnostics upon mismatch or corruption. Preserve referential consistency between DB rows and IFC entities.

### V. AI-Friendly & Session Memory
Design artifacts and workflows for small‑context LLM collaboration. Maintain a compact rotating context capsule (≤ 3 KB) containing: open DB path, storage mode (SQLite or MSSQL), schema version, active IFC file path, selected entity IDs, and current task summary. Persist at `.specify/memory/context-capsule.json`. Capture decisions as concise ADRs under `.specify/adr/`. Prompts, specifications, and transformation scripts live under `.specify/`. Prefer deterministic, text-first logs, metadata exports, and machine-diffable outputs.

### VI. Dual Storage Architecture (SQLite Settings + Optional MS SQL Project Data)
Application settings ALWAYS reside in the local SQLite settings database. Project data MAY live either:
1. In the same SQLite file (Local Mode), OR
2. In a Microsoft SQL Server database (Remote Mode) selected during project creation or migration.

Never persist the same project data concurrently in both backends. Remote Mode stores only project domain tables in MSSQL; local SQLite continues to store settings, connection descriptors, schema version ledger (covering both dialects), and minimal synchronization metadata.

Rules:
- Mode is immutable per project unless an explicit, user‑approved migration tool performs a one‑way copy (with dry run & report). Migration MUST be explicit and logged.
- Connection credentials are stored encrypted (Windows DPAPI or credential vault) or referenced via named ODBC DSN; never in plain text logs.
- All DB access uses parameterized queries; prohibit string concatenation for SQL except static DDL.
- Schema parity: logical model is uniform; dialect-specific DDL kept in paired migration scripts (e.g., `migrations/sqlite/NNNN_description.sql` and `migrations/mssql/NNNN_description.sql`). A migration number is considered applied only when recorded in the local settings DB with backend & timestamp.
- Failure isolation: if MSSQL is unreachable, the project opens in read‑only degraded mode (no writes) with clear UI status. No silent queueing of writes.
- Observability: MSSQL operations include timing, affected row count, and retry outcome in structured logs.
- No implicit fallback from MSSQL to SQLite for the same project once remote mode is established.
- Consistency: multi‑step domain operations use explicit transactions (or `BEGIN TRANSACTION` + commit/rollback) across MSSQL. Cross-backend distributed transactions are forbidden.
- Testing MUST include: connection failure handling, migration divergence detection, latency impact (simulated), and correctness of fallback to read-only.

Rationale: MSSQL option allows scaling project data volume and concurrency while retaining deterministic, user-owned local configuration and offline introspection.

---
## Technology & Constraints

- **Runtime**: Python 3.13 (Windows). Public APIs have type hints. Use stdlib `logging` (plain or JSON formatter). Avoid global mutable state except controlled singletons (e.g., `AppContext`).
- **GUI**: PySide6 only. UI updates happen on the main thread through signals. Use resource compilation (`pyside6-rcc`) as required.
- **Database (Core Settings)**: stdlib `sqlite3` with a row-factory returning dict-like objects (`sqlite3.Row` or wrapper). One definitive settings file per user/project. Backups and `VACUUM` are user-triggered. Schema changes via sequential migrations keyed by `user_version`.
- **Database (Project Data Optional Remote)**: Microsoft SQL Server via ODBC (`pyodbc`) or an alternative thin driver if pinned and vetted. Maintain a backend abstraction layer (e.g., `StorageGateway`) exposing uniform CRUD + query composition limited to common SQL subset. MSSQL-specific features (e.g., window functions, computed columns) require capability flags and MUST NOT break SQLite parity.
- **Dialect Differences Management**: Provide minimal SQL templating (no heavy ORM). Keep DDL explicit. For queries requiring syntax divergence (e.g., `AUTOINCREMENT` vs `IDENTITY`, `BOOLEAN` emulation), encapsulate in adapter functions. Migrations are idempotent per backend and recorded centrally in SQLite.
- **IFC**: IfcOpenShell (version pinned). Support open, query (entity retrieval, basic relationships), write (selected subsets), and export. Geometry operations are optional and guarded.
- **Files & Settings**: Never write outside user-chosen directories except logs and ephemeral state under `.specify/`. Connection secrets stored safely (not in git). Temporary export artifacts go to user-specified directories.
- **Security**: No embedded credentials in code. Enforce least-privilege MSSQL roles (DML + required metadata). Sensitive logs redact secrets. Handle UNC paths and long paths using Windows APIs.
- **Performance**: Use WAL for SQLite concurrency. Batch MSSQL writes inside a transaction. Avoid N+1 query loops—prefer set-based retrieval.

---
## Development Workflow

- Changes are small and reviewable with descriptive titles (Conventional Commit style preferred). Each merged change updates (or validates) the context capsule; architectural decisions produce a short ADR.
- Migration pipeline: add new migration file pair(s); update migration manifest; include tests proving forward migration & blank initialization equivalence. A PR introducing migrations must show resulting `PRAGMA user_version` and MSSQL schema diff summary.
- Tests focus on: SQLite schema init/migration; MSSQL schema init/migration; downgrade rejection paths; IFC import/export core cycle; UI non-interactive smoke (launch + open + close); adapter parity (selected CRUD scenarios produce equivalent logical results across backends).
- Dependency pinning: `requirements.txt` (hash-locked optional). Document install & run commands in `README`. Provide bootstrap script (`scripts/bootstrap.ps1`).
- Logging includes: operation name, target backend (sqlite|mssql), file or server/database name, duration, row count, and outcome (success|error). Error surfaces actionable remediation text in UI.
- Code review checklist includes: thread confinement, signal/slot correctness, migration idempotency, no duplicate storage, logging completeness, and IFC mapping preservation.

---
## Storage & Migration Model

| Concern | SQLite (Settings / Local Data) | MSSQL (Project Data) |
|---------|--------------------------------|----------------------|
| Authority for Mode | Single source | Referenced (no settings) |
| Migrations Ledger | Central (tracks both) | None (applied via scripts; recorded in SQLite) |
| Data Duplication | Not allowed if MSSQL active | Not allowed |
| Connection Handling | Direct file path | DSN / connection string (encrypted) |
| Transactions | Explicit BEGIN/COMMIT | Explicit, scoped |
| Offline Behavior | Full R/W | Read-only degraded (no writes) |

---
## Error Handling & Observability

- Uniform error taxonomy (`StorageError`, `MigrationError`, `IFCLoadError`, `ValidationError`).
- User-facing dialogs summarize failure, log ID, and suggested fix.
- Log structure (JSON option): `{ timestamp, level, op, backend, target, duration_ms, row_count, status, message }`.
- Health panel: shows current backend, schema version(s), pending migrations, last context capsule update time.

---
## Security & Privacy

- Redact: passwords, tokens, server names if flagged sensitive, file paths on user request (privacy mode). Default logs include full paths (transparency) unless privacy mode enabled.
- No telemetry without explicit user opt-in.
- Secrets never written to ADRs or capsule.

---
## Governance

This constitution defines non‑negotiable constraints. Amendments are required for:
- Runtime platform changes
- GUI framework changes
- Database ownership or storage mode changes (e.g., adding another remote backend)
- IFC handling model shifts (schema coverage, mapping strategy)
- AI/context persistence format adjustments exceeding size or structure constraints

Amendment PR Requirements:
1. Rationale & impact summary
2. Migration & rollback (if applicable)
3. Updated context capsule example
4. Updated version + amendment date
5. Test plan adjustments

Reviews must verify strict compliance before merge. Violations discovered post-merge trigger an immediate corrective issue.

---
## Versioning & Compliance

- Constitution version increments MINOR for additive governance changes; MAJOR for breaking constraints; PATCH for clarifications.
- Tooling MAY include a compliance script that scans for disallowed patterns (e.g., ORM imports, raw unparameterized SQL, unsupported platform checks).
- Non-compliant PRs are blocked until corrected.

---
## Appendix A: Context Capsule Schema (≤ 3 KB Target)
```jsonc
{
  "db_settings_path": "C:/path/to/settings.sqlite",
  "storage_mode": "sqlite" | "mssql",
  "schema_version": 12,
  "pending_migrations": 0,
  "active_ifc_file": "C:/projects/sample.ifc",
  "selected_entity_ids": ["3fGx...", "0aK2..."],
  "current_tasks": "Importing IFC walls; normalizing attributes",
  "last_updated": "2025-09-19T12:34:56Z"
}
```

---
## Appendix B: Migration File Naming
- SQLite: `migrations/sqlite/0012_add_material_table.sql`
- MSSQL: `migrations/mssql/0012_add_material_table.sql`
- Both required unless backend-agnostic; if only one needed, add a no-op counterpart containing a header comment `-- no-op for backend parity`.

---
## Appendix C: Minimal Storage Adapter Interface (Illustrative)
```python
a: str
class StorageAdapter(Protocol):
    backend: Literal["sqlite", "mssql"]

    def connect(self) -> None: ...
    def close(self) -> None: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def execute(self, sql: str, params: Sequence[Any] = ()) -> Result: ...
    def executemany(self, sql: str, seq_params: Sequence[Sequence[Any]]) -> BatchResult: ...
    def query(self, sql: str, params: Sequence[Any] = ()) -> list[Row]: ...
    def supports_feature(self, feature: str) -> bool: ...
```

---
## Appendix D: ADR Template (≤ 400 words)
```
# ADR NNN: Title
Date: YYYY-MM-DD
Status: Proposed | Accepted | Superseded by ADR MMM
Context: <short problem statement>
Decision: <concise resolution>
Consequences: <positive/negative outcomes>
References: <links / issue IDs>
```

---
## Acceptance
By contributing, you agree to uphold this constitution. Proposals altering governed dimensions MUST follow the amendment process.
