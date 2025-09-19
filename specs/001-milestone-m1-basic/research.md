# Phase 0 Research – Milestone M1

## Objectives
Clarify foundational decisions for startup UX, storage mode handling, migration safety, logging differentiation, and recent projects persistence to eliminate ambiguities before design.

## Decisions & Rationale

### D1: Recent Projects Load Strategy
- Decision: Load once at application startup; no runtime refresh.
- Rationale: Simplicity and deterministic session state; avoids file watchers.
- Alternatives: Manual refresh action (rejected: out of scope); auto-refresh via polling (rejected: unnecessary complexity).

### D2: Recent Projects Cap
- Decision: Maximum 15 entries (configurable constant in code).
- Rationale: Keeps list concise and avoids UI clutter.
- Alternatives: Unlimited (rejected: unwieldy); user-configurable in UI (rejected: scope creep for M1).

### D3: De-duplication Policy
- Decision: On open/create success, remove existing matching path first, then prepend new entry with updated timestamp.
- Rationale: Ensures recency ordering without duplicates.
- Alternatives: Keep duplicates (rejected: confusing ordering).

### D4: Migration Atomicity & Backup Warning
- Decision: All migrations execute inside a single transaction (when supported); show a pre-migration modal advising user to back up the file.
- Rationale: Prevent partially applied migrations; user empowerment for safety.
- Alternatives: Stepwise commit per migration (rejected: risk of partial upgrade failures).

### D5: MSSQL Connection Testing
- Decision: Provide explicit Test Connection button; disable Create until success in current dialog state.
- Rationale: Prevent invalid remote mode creation.
- Alternatives: Implicit test on Create (rejected: poorer user feedback loop).

### D6: Read-Only Remote Mode Fallback
- Decision: If MSSQL unreachable at open, set project state to read-only; log warning; allow user to retry connect later.
- Rationale: Read access may still be useful; avoids blocking inspection.
- Alternatives: Block open entirely (rejected: reduces utility).

### D7: Log Severity Differentiation
- Decision: Three levels: INFO (neutral text), WARNING (amber icon/prefix), ERROR (red icon/prefix). Future expansion reserved.
- Rationale: Minimal yet clear triage.
- Alternatives: Verbose multi-level (debug/trace) (rejected: M1 scope minimalism).

### D8: Credential Handling
- Decision: Store only non-secret MSSQL parameters in SQLite; do not persist password unless later secret-store integration added (placeholder). Prompt each session if password absent.
- Rationale: Minimizes accidental exposure risk.
- Alternatives: Plain-text storage (rejected: security risk).

### D9: Schema Version Representation
- Decision: Semantic version string in `meta` table key `schema_version`; internal numeric migration sequence tracked separately (e.g., `migrations_applied` table for future phases) but M1 uses only baseline.
- Rationale: Future-friendly while keeping M1 minimal.
- Alternatives: Pure integer only (rejected: less expressive for stakeholders), multiple keys (rejected: redundant).

### D10: Failure Messaging Pattern
- Decision: User-facing messages include action + target + remediation suggestion (e.g., "Migration failed: missing table. Restore backup or re-create project.").
- Rationale: Actionable guidance reduces support burden.

## Open Risks
- Lack of secret storage integration may reduce convenience (password re-entry). Mitigation: Document expected behavior.
- Single-transaction migration may be limited if future migrations require pragma changes outside transaction. Mitigation: Consider staged design later.

## Alignment With Constitution
- Windows + Python only (implied; no cross-platform elements introduced here).
- User-managed SQLite preserved; optional MSSQL remote mode consistent with dual storage principle.
- Logging strategy meets structured clarity requirement.

## Outcome
All initial unknowns clarified; no remaining NEEDS CLARIFICATION markers for M1.
