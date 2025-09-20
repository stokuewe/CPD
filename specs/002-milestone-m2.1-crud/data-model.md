# Phase 1: Data Model — Milestone M2.1

Source of truth: sqlite.sql and azure.sql (must remain in sync; no schema changes).

## Entities

### canonical_psets
- pset_id: INTEGER/INT, PK
- name: TEXT/NVARCHAR(255), UNIQUE, NOT NULL
- created_at/by, updated_at/by: timestamps, audit (nullable)

### canonical_units
- unit_id: INTEGER/INT, PK
- name: TEXT/NVARCHAR(255), UNIQUE, NOT NULL
- symbol: TEXT/NVARCHAR(50), optional
- created_at/by, updated_at/by

### canonical_datatypes
- type_id: INTEGER/INT, PK
- name: TEXT/NVARCHAR(255), UNIQUE, NOT NULL
- created_at/by, updated_at/by

### canonical_value_domains
- domain_id: INTEGER/INT, PK
- name: TEXT/NVARCHAR(255), UNIQUE, NOT NULL
- created_at/by, updated_at/by

### canonical_value_items
- item_id: INTEGER/INT, PK
- domain_id: INTEGER/INT, NOT NULL → FK canonical_value_domains(domain_id) ON DELETE CASCADE
- code: TEXT/NVARCHAR(255), NOT NULL (machine code)
- label: TEXT/NVARCHAR(255), optional (human label)
- created_at/by, updated_at/by

### canonical_attributes
- attr_id: INTEGER/INT, PK
- pset_id: INTEGER/INT, NOT NULL → FK canonical_psets(pset_id) ON DELETE CASCADE
- name: TEXT/NVARCHAR(255), NOT NULL (unique within pset — app-level)
- datatype: TEXT/NVARCHAR(128), optional (free-form; UI constrained to canonical set)
- unit_id: INTEGER/INT, optional → FK canonical_units(unit_id) ON DELETE SET NULL
- value_domain_id: INTEGER/INT, optional → FK canonical_value_domains(domain_id) ON DELETE SET NULL
- created_at/by, updated_at/by

## Relationships
- Pset 1—N Attributes
- Attribute —(0..1)→ Unit
- Attribute —(0..1)→ ValueDomain
- ValueDomain 1—N ValueItems
- Mappings reference canonical entities (map_ifc_psets, map_ifc_attrs, map_ifc_units, map_ifc_types, map_ifc_values)

## Validation Rules (App-Level)
- Pset.name unique (DB-enforced), trimmed, 1–100 chars, allowed [A–Z a–z 0–9 _ - space], case-insensitive normalize for checks
- Attribute.name unique within Pset (enforced in app), same normalization as above
- Datatype allowed values (UI): {text, integer, real, boolean, date, datetime}
- Value domain item labels unique within a domain (case-insensitive normalized)

## Notes
- No schema changes in M2.1. All constraints beyond DB-enforced uniqueness are handled at the application layer consistently across SQLite and MSSQL.

