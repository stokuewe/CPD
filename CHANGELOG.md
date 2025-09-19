# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to the binding CONSTITUTION.md and synchronized schemas (sqlite.sql, azure.sql).

## [M1] - Basic GUI, Startup, and Database Connection (completed)
- GUI launcher added: `python -m src.app.run`
- Startup window with:
  - Recent projects list (cap 10, dedup, move-to-top)
  - Buttons: Open Project, Create Project, Clear Recent
  - Log pane with adaptive contrast (light/dark)
- Recent list interactions:
  - Double-click or Enter to open
  - Right-click context menu: Open, Remove from Recent
  - Open Project button shows file dialog unless a recent item is explicitly selected
- Create Project flow:
  - Local (SQLite): applies sqlite.sql to new file; updates Recent
  - Remote (MSSQL): connection dialog with Test Connection; stores descriptor locally (no password)
- Responsiveness:
  - Busy cursor for short tasks; progress dialog appears for tasks >= 1 second
- Services:
  - RecentProjectsService with persistence in user scope; `remove(path)` added
  - Local/Remote project creators
  - Logging model with redaction
- Tests:
  - Unit: paths, redaction, MSSQL connection, migrations, recent projects (including remove)
  - Integration: responsiveness, startup view wiring, open without selection uses file dialog
- Docs:
  - README updated with GUI usage and recent list behavior
  - docs/quickstart-m1.md updated with recent list interactions

## [Unreleased]
- Planning for next milestone

