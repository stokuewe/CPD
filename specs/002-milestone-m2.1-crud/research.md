# Phase 0: Research — Milestone M2.1 CRUD Editor

## Context
Feature: Canonical dictionary editor for Psets and Attributes with datatype, optional unit, optional value domain; manage value domain entries; log all actions; persist to DB; performance budgets; no schema changes.

## Unknowns and Decisions

1) Datatype handling for canonical_attributes.datatype
- Decision: Keep as free-form label in DB (per schema), but constrain UI to canonical set: {text, integer, real, boolean, date, datetime (UTC)}.
- Rationale: Schema already models datatypes as free-form; canonical_datatypes exists for mapping contexts. Enforcing UI set ensures consistency without schema changes.
- Alternatives: Hard DB FK to canonical_datatypes — rejected (schema change not allowed).

2) Uniqueness enforcement
- Decision: Enforce in application layer: canonical_psets.name unique (DB-enforced), and (pset_id, name) unique for canonical_attributes (app-level check with case-insensitive normalized comparison).
- Rationale: DB does not enforce attribute uniqueness within pset; requirement mandates it; enforce before write to avoid errors across both backends.
- Alternatives: Add UNIQUE(pset_id, name) — rejected (schema change not allowed).

3) Units dictionary usage
- Decision: Attribute.unit_id selectable from canonical_units only; no creation in M2.1.
- Rationale: Matches spec and schemas.

4) Value Domain management
- Decision: CRUD on canonical_value_domains and canonical_value_items; prevent duplicate labels per domain (case-insensitive normalized) in UI; cascade delete via FK (DB ensures items removed when domain deleted).
- Rationale: Aligns with schemas (CASCADE on items).

5) Deletion safeguards
- Decision: Block deletion of Psets/Attributes if referenced in map_ifc_* tables; show counts and guidance.
- Rationale: Prevent breaking mappings; aligns with FR-009.
- Alternatives: Soft-delete — rejected (scope excludes soft-delete).

6) Logging
- Decision: Log all actions with severity + timestamp to app log window; redact sensitive info; include backend (sqlite|mssql), target, duration, row_count where sensible.
- Rationale: Constitution observability rules; FR-011.

7) Performance
- Decision: Use background threads for DB IO; batch reads; lazy-load attributes per expanded Pset; maintain in-memory index for search/filter.
- Rationale: Meet latency budgets; keep UI responsive.
- Alternatives: Full eager load — rejected for large datasets.

8) Cross-backend parity
- Decision: Use StorageGateway abstraction with parameterized SQL for both SQLite and MSSQL; identical semantics.
- Rationale: Constitution parity requirement.

## Result
All NEEDS CLARIFICATION resolved within the scope of M2.1 without schema changes. Ready for Phase 1.

