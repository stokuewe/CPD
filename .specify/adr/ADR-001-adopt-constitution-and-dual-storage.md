# ADR 001: Adopt Constitution v1.1.0 and Dual Storage Architecture
Date: 2025-09-19
Status: Accepted

Context: The project required a binding constitution and a scalable storage model. We target Windows 10/11 with Python 3.13 and a PySide6 GUI. Settings must be user-owned in SQLite, with an option to host project data in Microsoft SQL Server.

Decision: Adopt the Project Constitution v1.1.0 as canonical governance for development and operations. Establish dual storage architecture: settings and migrations ledger remain in local SQLite; project data MAY reside in MSSQL (Remote Mode) or in the same SQLite file (Local Mode). The canonical constitution file is `.specify/memory/constitution.md` (mirrored at `CONSTITUTION.md`). Context capsule persists at `.specify/memory/context-capsule.json`. ADRs live under `.specify/adr/`.

Consequences:
- Deterministic platform (Windows + Python 3.13) and GUI-first (PySide6) constraints.
- Schema parity enforced via paired migration scripts for SQLite and MSSQL; migrations recorded centrally in SQLite.
- No duplicate project data across backends; Remote Mode degrades to read-only on connectivity failure.
- All DB access uses parameterized queries; secrets handled via DPAPI/credential vault or DSN.
- Tests must cover initialization/migrations for both backends, divergence detection, and failure handling.

References:
- Constitution v1.1.0: `CONSTITUTION.md` (canonical: `.specify/memory/constitution.md`)
- Context Capsule path: `.specify/memory/context-capsule.json`

