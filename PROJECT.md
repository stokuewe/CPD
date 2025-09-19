# 📘 Project Specification: CPD – Common Project Database

## 🏗️ Introduction & Overview
The **Common Project Database (CPD)** is a Windows desktop application built with **Python + PySide**.  
Its purpose is to provide a central hub for importing, standardizing, and enriching project attribute data from different construction-related sources.  

- Focus: **attribute and metadata management** (not 3D geometry).  
- Database-first approach: each project is represented by a **SQLite database** (default) or linked to **MSSQL** for enterprise use.  
- Development is structured into **Milestones (M1–M5)**, each delivering a clear, testable slice of functionality.  

---

## 🗂️ High-Level Architecture

The system is layered to ensure modularity and extensibility:  

```
+--------------------------------------------------+
|                  GUI Layer (PySide)              |
|  - Main Window / Startup Screen                  |
|  - CRUD Editors (canonical tables, mappings)     |
|  - Log Window, Status Views, Automation Manager  |
+--------------------------------------------------+
|              Application Logic Layer             |
|  - Project Management (open/create, migration)   |
|  - Import/Export Handlers (IFC, Excel, etc.)     |
|  - Mapping Engine (staging → canonical)          |
|  - Automation Engine (tasks, queue, scheduler)   |
|  - Enrichment Engine (cross-source rules)        |
+--------------------------------------------------+
|                 Database Layer                   |
|  - SQLite (default, local project file)          |
|  - MSSQL (optional, external enterprise mode)    |
|  - Schema versioning & migration support         |
+--------------------------------------------------+
```

📌 **Milestones progressively fill out the layers**:  
- **M1:** GUI basics + DB connection (SQLite/MSSQL).  
- **M2:** Add IFC staging/canonical/mapping.  
- **M3:** Extend to Powerproject, Excel/CSV, Revit.  
- **M4:** Add automation engine.  
- **M5:** Add enrichment engine (cross-source linking).  

---

## 🧭 Milestones

### 🧭 Milestone M1: Basic GUI, Startup, and Database Connection
**🎯 Goal**  
Lay the foundation: project lifecycle handling (open/create), SQLite/MSSQL connection, schema versioning, and logging.  

**📦 Scope**  
- PySide GUI with startup screen, recent projects list, log window.  
- Create/open project (SQLite or MSSQL-backed).  
- Schema versioning with migration support.  
- Recent project tracking (`recent_projects.json`).  

**✅ Completion Criteria**  
- User can create/open a project with schema checks and logging.  
- MSSQL connections can be tested before saving.  
- Recent projects persist between sessions.  

---

### 🧭 Milestone M2: IFC Import & Canonical Standardization
**🎯 Goal**  
Enable importing of IFC files and establish canonical standards for attribute mapping.  

**📦 Scope**  
- Import IFC files into **staging tables**.  
- Bootstrap **canonical tables** from a “golden IFC”.  
- CRUD editor for managing canonical attributes and values.  
- Mapping between staging and canonical tables.  
- Export standardized attribute data.  

**✅ Completion Criteria**  
- User can import IFCs, define canonical standards, map attributes, and export normalized data.  

---

### 🧭 Milestone M3: Additional Data Sources
**🎯 Goal**  
Expand CPD to handle additional data sources beyond IFC.  

**📦 Scope**  
- Import Powerproject schedules (SQLite).  
- Import Excel/CSV files.  
- Connect to Revit via direct plugin (no staging import, mapping only).  
- Unified mapping engine across all sources.  

**✅ Completion Criteria**  
- User can integrate multiple data sources into the canonical model.  

---

### 🧭 Milestone M4: Automation
**🎯 Goal**  
Automate data handling tasks to reduce manual work.  

**📦 Scope**  
- Automation Manager in GUI.  
- Define tasks (imports, exports, mappings).  
- Trigger tasks on schedule or file changes.  
- Task queue (sequential, no overlaps).  
- Status & logs visible in GUI.  

**✅ Completion Criteria**  
- Automation tasks run reliably in sequence with clear status reporting.  

---

### 🧭 Milestone M5: Cross-Source Enrichment
**🎯 Goal**  
Allow data to flow between sources through user-defined connection rules.  

**📦 Scope**  
- Define **connection rules** (e.g., link schedule dates to IFC attributes).  
- Apply enrichment during automation tasks.  
- Manage and edit rules in GUI.  

**✅ Completion Criteria**  
- Data from one source enriches another automatically via rules.  

---

## 📅 Roadmap Wrap-Up
CPD grows incrementally:  
- **M1** secures the foundation (GUI + DB).  
- **M2–M3** expand import and mapping capabilities.  
- **M4–M5** add automation and cross-source intelligence.  

This milestone approach ensures **robustness at each stage** and keeps the system **flexible for future extensions** (e.g., APIs, dashboards, advanced reporting).  
