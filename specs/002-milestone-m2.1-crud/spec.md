# Feature Specification: Milestone M2.1 — CRUD Editor for Canonical Standards

**Feature Branch**: `002-milestone-m2-1`
**Created**: 2025-09-19
**Status**: Draft
**Input**: User description: "Provide a GUI editor to create, read, update, delete canonical Psets and Attributes with metadata (datatype, unit, value domain), manage value domain entries, log actions, and persist to the project DB. Completion: users can CRUD Psets/Attributes, assign/edit datatypes/units/value domains, manage value-domain values, logs show actions, and all changes persist."

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
- Mandatory sections: Must be completed for every feature
- Optional sections: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
1. Mark all ambiguities: Use [NEEDS CLARIFICATION: specific question]
2. Don't guess: If the prompt doesn't specify something, mark it
3. Think like a tester: Every vague requirement should fail the "testable and unambiguous" checklist item
4. Common underspecified areas:
   - User types and permissions
   - Data retention/deletion policies
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## User Scenarios & Testing (mandatory)

### Primary User Story
As a project user, I want to maintain a canonical dictionary of Property Sets (Psets) and their Attributes (with datatype, unit, optional value domain), so that IFC data can be standardized and consistently interpreted across the project.

### Acceptance Scenarios
1. Given an opened project with no canonical definitions, when the user opens the Canonical Editor, then they see an empty dictionary with options to add a Pset.
2. Given an opened project, when the user adds a new Pset with a unique name and optional description, then the Pset appears in the list/tree and a confirmation is logged.
3. Given a selected Pset, when the user adds a new Attribute with a unique name (within that Pset) and selects a datatype (and optionally unit and value domain), then the Attribute appears under the Pset and is logged.
4. Given existing canonical entries, when the user edits a Pset or Attribute (e.g., rename, change datatype/unit/value domain), then the change is saved immediately and the log records old → new.
5. Given a Pset containing Attributes, when the user deletes the Pset, then a confirmation warns that all contained Attributes will be removed; upon confirmation, all are removed and the action is logged.
6. Given a selected Attribute with a value domain, when the user adds/removes/renames allowed values, then the side panel updates and the actions are logged.
7. Given attempted duplication (same Pset name globally, or same Attribute name within its Pset), when the user saves, then the system prevents the change and displays a clear warning; the attempt is logged as a warning.
8. Given an error condition (e.g., database write fails), when the user attempts to save, then the user receives an actionable error and no partial/invalid data is committed; the error is logged.
9. Given many Psets/Attributes (~500 Psets, ~5,000 Attributes), when the editor is opened, then the list/tree loads within ≤ 1.5 s and remains responsive during CRUD actions (expand ≤ 150 ms; add/edit/delete ≤ 200 ms median; search/filter ≤ 150 ms).
10. Given changes made in the editor, when the user closes the editor, then all committed changes persist to the project database and a final confirmation is logged.

### Edge Cases
- Empty dictionary (no Psets): editor should clearly indicate emptiness and guide the user to "Add Pset".
- Name collisions with different letter case: Names are case-insensitive unique on a normalized form; collisions are rejected with guidance.
- Deleting a Pset referenced elsewhere (e.g., mappings): Block deletion if in use; show “Cannot delete ‘X’ because it is used by N mappings. Remove those first.”
- Changing an Attribute's datatype when existing mappings/values depend on it: Allow only safe changes (integer↔real, date↔datetime) when not in use; otherwise block with explanation.
- Value domain duplicates (same label twice): Prevent duplicates within a domain (case-insensitive normalized labels).
- Large lists (hundreds/thousands of Psets/Attributes): Provide search/filter; no pagination in M2.1; Psets collapsed by default.
- Undo/redo support: Out of scope in M2.1; use confirmations for destructive actions and log all changes.

## Requirements (mandatory)

### Functional Requirements
- FR-001: Users MUST be able to open a Canonical Editor from the main application after opening a project.
- FR-002: The editor MUST display a list/tree of canonical Psets; expanding a Pset MUST show its Attributes.
- FR-003: Users MUST be able to create a new canonical Pset with a unique name and optional description.
- FR-004: Users MUST be able to create a new canonical Attribute under a selected Pset with a unique name (within that Pset).
- FR-005: Users MUST be able to assign/edit an Attribute's datatype from the set: text, integer, real, boolean, date, datetime (datetime in UTC).
- FR-006: Users MUST be able to assign/edit an Attribute's unit by selecting from the project-level canonical Units dictionary; selection is optional; no ad-hoc unit creation in M2.1.
- FR-007: Users MUST be able to associate an Attribute with an optional value domain and manage its allowed values (add, rename, remove); duplicates MUST be prevented within a domain (case-insensitive normalized).
- FR-008: Users MUST be able to edit Pset name/description and Attribute name/metadata; changes MUST be persisted automatically.
- FR-009: Users MUST be able to delete a Pset (with confirmation that its Attributes will be deleted) and delete individual Attributes; deletion MUST be blocked if the item is referenced elsewhere (e.g., by mappings) with a clear message; no soft-delete.
- FR-010: The system MUST prevent duplicates (Pset name globally; Attribute name within its Pset) using case-insensitive comparisons on a normalized form with clear user feedback.
- FR-011: All actions (add/edit/delete) MUST be logged to the application's log window with severity and timestamp.
- FR-012: On any error (validation or persistence), the system MUST show actionable messages and avoid partial updates.
- FR-013: All changes MUST be persisted to the project database in compliance with the existing schemas (sqlite.sql and azure.sql). No schema changes are implied by this feature.
- FR-014: The editor MUST handle empty states gracefully and provide guidance to first-time users (e.g., "Add Pset").
- FR-015: The editor MUST remain responsive with typical dataset sizes (≈500 Psets, ≈5,000 Attributes); initial open ≤ 1.5 s; expand Pset ≤ 150 ms; add/edit/delete ≤ 200 ms median; search/filter ≤ 150 ms.
- FR-016: Names and labels MUST meet constraints: length 1–100 (descriptions up to 500); allowed characters [A–Z a–z 0–9 _ - space]; trimmed; normalized; uniqueness checks use case-insensitive comparisons.
- FR-017: Behavior MUST be consistent between local (SQLite) and remote (MSSQL) projects.
- FR-018: The feature MUST not expose or log sensitive information; logs MUST follow redaction rules already established.
- FR-019: Changing an Attribute’s datatype MUST be allowed only for safe conversions (integer↔real; date↔datetime) and only when not in use; otherwise the change MUST be blocked with an explanation.


### Key Entities (include if data involved)
- Canonical Pset: A named grouping of canonical Attributes with an optional description; globally unique by name. Stored and constrained as per existing schema.
- Canonical Attribute: A named property within a Pset; unique within its Pset; has metadata (datatype, optional unit, optional value domain reference) as defined by existing schema.
- Datatype Dictionary: Canonical set: text, integer, real, boolean, date, datetime (datetime in UTC). Aliases permitted in UI (e.g., 'string'→text; 'float/decimal'→real); stored as canonical values.
- Unit Dictionary: Project-level canonical units; the editor selects from existing units only (no creation in M2.1); localization of unit labels is out of scope for M2.1.
- Value Domain: An optional set of allowed values that can be linked to an Attribute; includes a list of Value Domain Entries (labels/values). Constraints are defined by existing schema.
- Relationships: Pset ←contains— Attribute; Attribute —may reference→ Datatype, Unit, Value Domain; definitions and referential integrity follow sqlite.sql and azure.sql (no changes in this milestone).

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous (where specified)
- [x] Success criteria are measurable (via CRUD actions, logging, persistence)
- [x] Scope is clearly bounded (CRUD/editor only; no schema changes)
- [x] Dependencies and assumptions identified (existing schemas; logging model)

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
