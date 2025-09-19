# Quickstart – Milestone M1

Goal: Launch application, create/open project (SQLite or MSSQL mode), observe logging, verify recent projects persistence.

## Prerequisites
- Windows 10/11
- Python 3.13 installed
- Dependencies installed (placeholder: will define in root requirements)
- Optional: MSSQL Server reachable + ODBC driver installed

## Steps
1. Launch application executable / `python -m app` (TBD entry point).
2. On startup screen, review (possibly empty) Recent Projects list.
3. Click "Create Project".
4. Choose project path (e.g., `C:/Projects/demo.sqlite`).
5. Select Storage Mode:
   - SQLite: Proceed to step 7.
   - MSSQL: Fill server, database, auth type, (username/password if SQL auth).
6. Click "Test Connection"; expect success log entry. If failure, adjust parameters until success.
7. Confirm creation → expect success and baseline schema_version logged.
8. Close application; relaunch → project appears at top of Recent Projects list.
9. Open project → expect validation log and confirmation message.
10. Trigger an error scenario (e.g., open invalid file) → observe ERROR log differentiation.
11. Use "Clear Recent List" action → list empties and is persisted.

## Expected Outcomes
- Log window displays INFO entries for start, open/create, migration check, and confirmation.
- WARNING displayed if MSSQL unreachable in remote open attempt (project opens read-only).
- ERROR displayed for invalid DB file attempts.
- Recent projects list persists across sessions (max 15, de-duplicated).

## Validation Checklist
- [ ] Create SQLite project success
- [ ] Create MSSQL-backed project success (optional environment)
- [ ] Migration warning shown for outdated schema (simulate by modifying version)
- [ ] Read-only mode set when MSSQL offline
- [ ] Recent list trimming after >15 entries
- [ ] Clear list action works
- [ ] No secrets exposed in logs

## Next Phases
Post M1 adds domain data schemas, richer migration ledger, context capsule integration, and IFC interactions.
