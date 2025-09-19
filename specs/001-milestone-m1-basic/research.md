# Phase 0: Research

## Decisions
- Recent projects handling
  - Cap list at 10; move-to-top on re-open; drop missing files on load; de-duplicate
  - Store in user-scope application data directory; path and last-opened timestamp
  - Clear action resets to empty list file
- Migration + recovery
  - Transactional and durable migrations; pre-migration backup created alongside DB
  - On interruption, a recovery marker enables Resume / Restore backup / Cancel
  - Refuse open when schema is newer than app version
- UI responsiveness + progress
  - Busy indicator for operations >200 ms; progress dialog >1 s (cancel where safe)
- Logging
  - In-GUI INFO/WARN/ERROR with emphasis; optional daily-rotated file log
  - Secrets redacted; never log passwords or full connection strings
- MSSQL connectivity
  - Support SQL and Windows Authentication; secure by default; developer override for certificate trust with explicit consent
  - Do not store passwords in M1; prompt per connect
- Remote Mode unavailable
  - If server unreachable, block project open with actionable error (no degraded read-only mode in M1)
- Schema versioning
  - Initial version 1.0.0; sequential migrations for older versions; refuse newer

## Rationale
- Usability: cap + de-dup keeps recent list manageable; visual logging increases transparency
- Safety: pre-migration backup and recovery marker prevent data loss paths
- Security: no password storage in M1 reduces risk and implementation scope
- Performance: explicit responsiveness thresholds set expectations and testing targets
- Governance: constitution requires Windows + PySide6 + SQLite settings; plan adheres and avoids schema changes

## Alternatives Considered
- Persisting passwords (DPAPI): rejected for M1 to minimize scope; consider later milestone with explicit opt-in
- Degraded read-only mode for Remote Mode: deferred; adds complexity and edge cases; can be designed later per constitution
- Long recent list (>10): rejected for discoverability; can be made configurable post-M1

