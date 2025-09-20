# Quickstart — Validate M2.1 Canonical CRUD

1) Open a project and launch the Canonical Editor
- Expect empty state guidance when no entries exist.

2) Create a Pset
- Add new Pset with unique name; see it in list; success logged.

3) Add an Attribute
- Select Pset; add Attribute with unique name (within Pset); choose datatype; optionally choose unit and value domain; success logged.

4) Manage Value Domain Items
- For an Attribute with a value domain, add/rename/remove allowed values; duplicates prevented (case-insensitive); actions logged.

5) Edit Entries
- Rename Pset/Attribute; change datatype/unit/value domain; changes persist immediately; logs show old → new.

6) Delete with Safeguards
- Delete Attribute or Pset (with confirmation); block deletion if referenced by mappings; show actionable message.

7) Error Handling
- Simulate DB write failure; verify actionable error; no partial writes; log entry with severity.

8) Performance Checks
- With ~500 Psets and ~5,000 Attributes: open editor ≤ 1.5 s; expand ≤ 150 ms; add/edit/delete ≤ 200 ms median; search/filter ≤ 150 ms.

9) Persistence
- Close and reopen editor; all changes persist in project DB (SQLite or MSSQL mode) with identical behavior.

