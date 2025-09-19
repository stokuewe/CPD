# 🧭 Milestone M1: Basic GUI, Startup, and Database Connection

## 🎯 Goal
Establish the foundational structure for the application, including the GUI framework, project selection/creation flow, database connectivity (SQLite and optional MSSQL), and logging. This milestone ensures users can start working with a project safely, with clear feedback and robust version control.

## 🧑‍💻 User Journey

1. **Startup**  
   The user launches the application. The main GUI opens, displaying:
   - A list of recently opened projects (loaded from a local `recent_projects.json` file).
   - Options to:
     - Open an existing project file via file browser
     - Create a new project

2. **Opening an Existing Project**  
   - The user selects a `.sqlite` file.
   - The application checks the database schema version stored in the file (e.g., via a `meta` table).
   - If the schema is outdated:
     - The application performs a **migration step** to update the schema to match the current software version.
     - Migration steps are logged in the log window.
   - If migration is not possible (e.g., corrupt or incompatible schema), the user is shown a clear error message and the project is not loaded.

3. **Creating a New Project**  
   - The user chooses where to save the new project file.
   - During creation, the user selects where project data will be stored:
     - **Option 1:** Store all data in the local SQLite file (default)
     - **Option 2:** Store only settings in SQLite, and connect to an external **MSSQL Server** for data storage

   - If MSSQL is selected:
     - A GUI form is shown for entering connection parameters:
       - Server name / instance
       - Database name
       - Port (optional)
       - Authentication type (SQL login or Windows auth)
       - Username / password (if applicable)
     - A **"Test Connection"** button validates the credentials and connection before saving.
     - If the connection fails, a descriptive error is shown in the log window, and the project creation is halted until resolved.

4. **Project Initialization**
   - Once the project is opened or created, a confirmation message is logged.
   - The project’s settings, including the MSSQL configuration if used, are stored inside the SQLite file and can later be edited via a **Settings Window**.

## 🪵 Log Window
- All key actions (opening/creating project, schema check/migration, connection status, errors) are logged in real-time in a dedicated log window within the GUI.
- Errors are clearly differentiated (e.g., color-coded or prefixed) to alert the user.

## 📁 Recent Projects Handling
- Recently opened project paths are saved in a local `recent_projects.json` file (stored in the user’s config directory or application folder).
- The list is updated each time a project is successfully opened or created.
- The GUI provides an option to clear the recent projects list.

## 🧠 Schema Versioning and Migration
- Each project database includes a `meta` table containing the schema version (e.g., `schema_version = 1.0.0`).
- On load, the application checks whether the schema version is compatible with the current software version.
- If the schema is outdated:
  - A versioned **migration script** or function is triggered to update the schema.
  - Migration logs are shown in the log window.
- If the schema is incompatible or unrecognized, the user is notified, and the project is not loaded.

## ✅ Milestone M1 Completion Criteria
- GUI starts and displays recent projects and project options
- Opening an existing SQLite project:
  - Verifies schema version
  - Migrates if needed
  - Loads if compatible
- Creating a new SQLite project:
  - Offers choice between local-only or MSSQL-backed data
  - Collects MSSQL connection info with connection testing
- All actions produce appropriate log messages in a GUI log window
- Recent projects are tracked via `recent_projects.json`

---

## 🗃️ Database Schema

```sql
-- ------------------------------------------------------------
-- Table: meta
-- Purpose: Stores metadata about the project database itself,
--          especially the schema version for compatibility/migration checks.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Example entry:
-- ('schema_version', '1.0.0')

-- ------------------------------------------------------------
-- Table: settings
-- Purpose: General key-value storage for project-level settings.
--          Includes project name, storage mode, timestamps, etc.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Expected keys:
-- - 'project_name': Human-readable name of the project
-- - 'storage_mode': Either 'sqlite' or 'mssql'
-- - 'created_at': ISO 8601 timestamp of when the project was created

-- ------------------------------------------------------------
-- Table: mssql_connection
-- Purpose: Stores MSSQL server connection parameters when the
--          user chooses to connect to an external database.
--          Only one row is expected per project file.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mssql_connection (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    server TEXT NOT NULL,
    database TEXT NOT NULL,
    port INTEGER DEFAULT 1433,
    auth_type TEXT NOT NULL CHECK (auth_type IN ('sql', 'windows')),
    username TEXT,
    password TEXT
);
```