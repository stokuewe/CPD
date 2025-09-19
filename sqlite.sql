-- Enable FK enforcement in SQLite
PRAGMA foreign_keys = ON;

-- ============================================================
-- Table: meta
-- Purpose: Stores metadata about the project database itself,
--          especially the schema version for compatibility/migration checks.
-- Example: ('schema_version', '1.0.0')
-- ============================================================
CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,       -- Unique key (e.g., 'schema_version')
  value TEXT NOT NULL           -- Associated value (e.g., '1.0.0')
);

-- ============================================================
-- Table: settings
-- Purpose: General key-value storage for project-level settings.
-- Expected keys:
--   - 'project_name' : Human-readable name of the project
--   - 'storage_mode' : Either 'sqlite' or 'mssql'
--   - 'created_at'   : ISO 8601 timestamp for project creation
-- ============================================================
CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,       -- Setting name
  value TEXT NOT NULL           -- Setting value
);

-- ============================================================
-- Table: mssql_connection
-- Purpose: Stores MSSQL server connection parameters when the
--          user chooses to connect to an external database.
--          Only one row is expected per project file.
-- NOTE: Enforces singleton row via CHECK (id = 1).
-- ============================================================
CREATE TABLE IF NOT EXISTS mssql_connection (
  id        INTEGER PRIMARY KEY CHECK (id = 1),             -- Singleton row; intended to always be 1
  server    TEXT NOT NULL,                                   -- e.g., 'localhost\SQLEXPRESS'
  database  TEXT NOT NULL,                                   -- Target database name (e.g., 'BuildingData')
  port      INTEGER DEFAULT 1433,                            -- Optional; defaults to 1433
  auth_type TEXT NOT NULL CHECK (auth_type IN ('sql','windows')), -- 'sql' or 'windows'
  username  TEXT,                                            -- Nullable for Windows auth
  password  TEXT                                             -- WARNING: store securely (encrypt/secret manager)
);

-- ============================================================
-- Sources & Versions
-- Root sources of imported data and their immutable versions.
-- ============================================================

-- Root sources of imported data (e.g., folders/files/projects).
CREATE TABLE IF NOT EXISTS sources (
  source_id  INTEGER PRIMARY KEY,  -- Surrogate key
  name       TEXT NOT NULL,        -- Human-readable source name
  path_hash  TEXT NOT NULL,        -- Hash of input path for deduping
  created_at TEXT NOT NULL         -- Creation timestamp (ISO 8601)
);

-- Immutable snapshots/versions of a given source import.
-- Each version represents a full import pass.
CREATE TABLE IF NOT EXISTS source_versions (
  version_id         INTEGER PRIMARY KEY,
  source_id          INTEGER NOT NULL,
  import_time        TEXT NOT NULL,     -- When this version was imported (ISO 8601)
  file_hash          TEXT NOT NULL,     -- Hash of the input payload
  user_label         TEXT,              -- Optional friendly label
  parent_version_id  INTEGER,           -- Optional parent (branch/derivation)
  FOREIGN KEY (source_id)         REFERENCES sources(source_id)           ON DELETE CASCADE,
  FOREIGN KEY (parent_version_id)  REFERENCES source_versions(version_id) ON DELETE SET NULL
);

-- ============================================================
-- Staging (IFC-like structured input)
-- ============================================================

-- Reference: Property Sets discovered in IFC input for a given version.
CREATE TABLE IF NOT EXISTS staging_ifc_ref_psets (
  pset_id    INTEGER PRIMARY KEY,
  version_id INTEGER NOT NULL,
  name       TEXT NOT NULL,        -- IFC pset name
  FOREIGN KEY (version_id) REFERENCES source_versions(version_id) ON DELETE CASCADE
);

-- Reference: Data types discovered in IFC input for a given version.
CREATE TABLE IF NOT EXISTS staging_ifc_ref_dtypes (
  dtype_id   INTEGER PRIMARY KEY,
  version_id INTEGER NOT NULL,
  name       TEXT NOT NULL,        -- Discovered/source datatype label
  FOREIGN KEY (version_id) REFERENCES source_versions(version_id) ON DELETE CASCADE
);

-- Reference: Units discovered in IFC input for a given version.
CREATE TABLE IF NOT EXISTS staging_ifc_ref_units (
  unit_id    INTEGER PRIMARY KEY,
  version_id INTEGER NOT NULL,
  name       TEXT NOT NULL,        -- Unit name (e.g., meter)
  symbol     TEXT,                 -- Unit symbol (e.g., m)
  FOREIGN KEY (version_id) REFERENCES source_versions(version_id) ON DELETE CASCADE
);

-- Reference: IFC type names (e.g., IfcWall) for a given version.
CREATE TABLE IF NOT EXISTS staging_ifc_ref_types (
  type_id    INTEGER PRIMARY KEY,
  version_id INTEGER NOT NULL,
  name       TEXT NOT NULL,        -- IFC class/type label
  FOREIGN KEY (version_id) REFERENCES source_versions(version_id) ON DELETE CASCADE
);

-- Reference: Attribute definitions (pset + name) for a given version.
CREATE TABLE IF NOT EXISTS staging_ifc_ref_attrs (
  attr_id    INTEGER PRIMARY KEY,
  version_id INTEGER NOT NULL,
  pset_id    INTEGER NOT NULL,
  name       TEXT NOT NULL,        -- Attribute/property name
  dtype_id   INTEGER,              -- Suggested type
  unit_id    INTEGER,              -- Suggested unit
  FOREIGN KEY (version_id) REFERENCES source_versions(version_id) ON DELETE CASCADE,
  FOREIGN KEY (pset_id)    REFERENCES staging_ifc_ref_psets(pset_id)      ON DELETE CASCADE,
  FOREIGN KEY (dtype_id)   REFERENCES staging_ifc_ref_dtypes(dtype_id)    ON DELETE SET NULL,
  FOREIGN KEY (unit_id)    REFERENCES staging_ifc_ref_units(unit_id)      ON DELETE SET NULL
);

-- Elements/entities parsed from IFC.
CREATE TABLE IF NOT EXISTS staging_ifc_elements (
  element_id  INTEGER PRIMARY KEY,
  version_id  INTEGER NOT NULL,
  ifc_guid    TEXT NOT NULL,   -- Stable IFC GUID
  ifc_class   TEXT NOT NULL,   -- IFC entity class (e.g., IfcWall)
  name        TEXT,
  parent_guid TEXT,            -- Parent relationship by GUID if available
  type_id     INTEGER,         -- FK to ref_types
  raw_json    TEXT,            -- Raw source payload for diagnostics
  FOREIGN KEY (version_id) REFERENCES source_versions(version_id) ON DELETE CASCADE,
  FOREIGN KEY (type_id)    REFERENCES staging_ifc_ref_types(type_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_ifc_elements_guid  ON staging_ifc_elements(ifc_guid);
CREATE INDEX IF NOT EXISTS idx_ifc_elements_class ON staging_ifc_elements(ifc_class);

-- Property values for IFC elements (resolved to ref_attrs).
CREATE TABLE IF NOT EXISTS staging_ifc_propvals (
  propval_id INTEGER PRIMARY KEY,
  version_id INTEGER NOT NULL,
  element_id INTEGER NOT NULL,
  attr_id    INTEGER NOT NULL,
  dtype_id   INTEGER,    -- Optional override/specific dtype
  unit_id    INTEGER,    -- Optional override/specific unit

  -- Value slots (nullable)
  v_text     TEXT,       -- Textual value
  v_num      REAL,       -- Floating numeric value
  v_int      INTEGER,    -- Integer value
  v_bool     INTEGER,    -- Boolean-as-int (0/1)
  v_json     TEXT,       -- Structured value (JSON as text)
  v_date     TEXT,       -- Date value (ISO-8601 string)
  v_datetime TEXT,       -- Datetime value (ISO-8601 string)

  raw_json   TEXT,       -- Original raw field/value

  FOREIGN KEY (version_id) REFERENCES source_versions(version_id)       ON DELETE CASCADE,
  FOREIGN KEY (element_id) REFERENCES staging_ifc_elements(element_id)  ON DELETE CASCADE,
  FOREIGN KEY (attr_id)    REFERENCES staging_ifc_ref_attrs(attr_id)    ON DELETE CASCADE,
  FOREIGN KEY (dtype_id)   REFERENCES staging_ifc_ref_dtypes(dtype_id)  ON DELETE SET NULL,
  FOREIGN KEY (unit_id)    REFERENCES staging_ifc_ref_units(unit_id)    ON DELETE SET NULL
);

-- ============================================================
-- Canonical Dictionary
-- ============================================================

CREATE TABLE IF NOT EXISTS canonical_psets (
  pset_id    INTEGER PRIMARY KEY,
  name       TEXT NOT NULL UNIQUE, -- Canonical pset name
  created_at TEXT,
  created_by TEXT,
  updated_at TEXT,
  updated_by TEXT
);

CREATE TABLE IF NOT EXISTS canonical_units (
  unit_id    INTEGER PRIMARY KEY,
  name       TEXT NOT NULL UNIQUE,
  symbol     TEXT,
  created_at TEXT,
  created_by TEXT,
  updated_at TEXT,
  updated_by TEXT
);

CREATE TABLE IF NOT EXISTS canonical_datatypes (
  type_id    INTEGER PRIMARY KEY,
  name       TEXT NOT NULL UNIQUE,
  created_at TEXT,
  created_by TEXT,
  updated_at TEXT,
  updated_by TEXT
);

CREATE TABLE IF NOT EXISTS canonical_value_domains (
  domain_id  INTEGER PRIMARY KEY,
  name       TEXT NOT NULL UNIQUE,
  created_at TEXT,
  created_by TEXT,
  updated_at TEXT,
  updated_by TEXT
);

CREATE TABLE IF NOT EXISTS canonical_value_items (
  item_id    INTEGER PRIMARY KEY,
  domain_id  INTEGER NOT NULL,
  code       TEXT NOT NULL,  -- Machine code
  label      TEXT,           -- Human label
  created_at TEXT,
  created_by TEXT,
  updated_at TEXT,
  updated_by TEXT,
  FOREIGN KEY (domain_id) REFERENCES canonical_value_domains(domain_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS canonical_attributes (
  attr_id          INTEGER PRIMARY KEY,
  pset_id          INTEGER NOT NULL,
  name             TEXT NOT NULL,
  datatype         TEXT,      -- Free-form datatype label
  unit_id          INTEGER,
  value_domain_id  INTEGER,
  created_at       TEXT,
  created_by       TEXT,
  updated_at       TEXT,
  updated_by       TEXT,
  FOREIGN KEY (pset_id)         REFERENCES canonical_psets(pset_id)            ON DELETE CASCADE,
  FOREIGN KEY (unit_id)         REFERENCES canonical_units(unit_id)            ON DELETE SET NULL,
  FOREIGN KEY (value_domain_id) REFERENCES canonical_value_domains(domain_id)  ON DELETE SET NULL
);

-- ============================================================
-- Mappings (per-version alignment of source -> canonical)
-- ============================================================

CREATE TABLE IF NOT EXISTS map_ifc_psets (
  mapping_id         INTEGER PRIMARY KEY,
  version_id         INTEGER NOT NULL,
  src_pset           TEXT NOT NULL,
  canonical_pset_id  INTEGER NOT NULL,
  FOREIGN KEY (version_id)        REFERENCES source_versions(version_id) ON DELETE CASCADE,
  FOREIGN KEY (canonical_pset_id) REFERENCES canonical_psets(pset_id)    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS map_ifc_attrs (
  mapping_id          INTEGER PRIMARY KEY,
  version_id          INTEGER NOT NULL,
  src_pset            TEXT NOT NULL,
  src_attr            TEXT NOT NULL,
  canonical_attr_id   INTEGER NOT NULL,
  FOREIGN KEY (version_id)        REFERENCES source_versions(version_id) ON DELETE CASCADE,
  FOREIGN KEY (canonical_attr_id) REFERENCES canonical_attributes(attr_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS map_ifc_units (
  mapping_id          INTEGER PRIMARY KEY,
  version_id          INTEGER NOT NULL,
  src_unit            TEXT NOT NULL,
  canonical_unit_id   INTEGER NOT NULL,
  FOREIGN KEY (version_id)        REFERENCES source_versions(version_id) ON DELETE CASCADE,
  FOREIGN KEY (canonical_unit_id) REFERENCES canonical_units(unit_id)    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS map_ifc_types (
  mapping_id          INTEGER PRIMARY KEY,
  version_id          INTEGER NOT NULL,
  src_type            TEXT NOT NULL,
  canonical_type_id   INTEGER NOT NULL,
  FOREIGN KEY (version_id)        REFERENCES source_versions(version_id) ON DELETE CASCADE,
  FOREIGN KEY (canonical_type_id) REFERENCES canonical_datatypes(type_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS map_ifc_values (
  mapping_id                INTEGER PRIMARY KEY,
  version_id                INTEGER NOT NULL,
  canonical_attr_id         INTEGER NOT NULL,
  src_value                 TEXT NOT NULL,
  canonical_value_item_id   INTEGER NOT NULL,
  FOREIGN KEY (version_id)              REFERENCES source_versions(version_id)     ON DELETE CASCADE,
  FOREIGN KEY (canonical_attr_id)       REFERENCES canonical_attributes(attr_id)   ON DELETE CASCADE,
  FOREIGN KEY (canonical_value_item_id) REFERENCES canonical_value_items(item_id)  ON DELETE CASCADE
);
