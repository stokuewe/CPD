-- Azure SQL (T-SQL) schema
-- This script mirrors the SQLite schema but uses SQL Server types and syntax.
-- NOTE: The `mssql_connection` table is intentionally omitted per request.
-- All tables use "cpd-" prefix for MSSQL deployment.

---------------------------------------------------------------
-- Helpers
---------------------------------------------------------------
-- Default schema assumed: dbo

---------------------------------------------------------------
-- Table: cpd-meta
-- Purpose: Stores metadata about the project database itself,
--          especially the schema version for compatibility/migration checks.
-- Example: ('schema_version', '1.0.0')
---------------------------------------------------------------
IF OBJECT_ID(N'[dbo].[cpd-meta]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-meta] (
  [key]   NVARCHAR(255) NOT NULL CONSTRAINT [PK_cpd_meta] PRIMARY KEY,  -- Unique key (e.g., 'schema_version')
  [value] NVARCHAR(4000) NOT NULL                                       -- Associated value (e.g., '1.0.0')
);
GO

---------------------------------------------------------------
-- Table: cpd-settings
-- Purpose: General key-value storage for project-level settings.
-- Expected keys:
--   - 'project_name' : Human-readable name of the project
--   - 'storage_mode' : Either 'sqlite' or 'mssql'
--   - 'created_at'   : ISO 8601 timestamp for project creation
---------------------------------------------------------------
IF OBJECT_ID(N'[dbo].[cpd-settings]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-settings] (
  [key]   NVARCHAR(255) NOT NULL CONSTRAINT [PK_cpd_settings] PRIMARY KEY,  -- Setting name
  [value] NVARCHAR(4000) NOT NULL                                           -- Setting value
);
GO

---------------------------------------------------------------
-- Sources & Versions
---------------------------------------------------------------
IF OBJECT_ID(N'[dbo].[cpd-sources]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-sources] (
  [source_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_sources] PRIMARY KEY, -- Surrogate key
  [name] NVARCHAR(255) NOT NULL,          -- Human-readable source name
  [path_hash] NVARCHAR(255) NOT NULL,     -- Hash of input path for deduping
  [created_at] DATETIME2(3) NOT NULL      -- Creation timestamp
);
GO

IF OBJECT_ID(N'[dbo].[cpd-source_versions]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-source_versions] (
  [version_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_source_versions] PRIMARY KEY,
  [source_id] INT NOT NULL,
  [import_time] DATETIME2(3) NOT NULL, -- When this version was imported
  [file_hash] NVARCHAR(255) NOT NULL,  -- Hash of the input payload
  [user_label] NVARCHAR(255) NULL,     -- Optional friendly label
  [parent_version_id] INT NULL,        -- Optional parent (branch/derivation)
  CONSTRAINT [FK_cpd_source_versions_sources]
    FOREIGN KEY ([source_id]) REFERENCES [dbo].[cpd-sources]([source_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_source_versions_parent]
    FOREIGN KEY ([parent_version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE NO ACTION
);
GO

---------------------------------------------------------------
-- Staging (IFC-like structured input)
---------------------------------------------------------------
IF OBJECT_ID(N'[dbo].[cpd-staging_ifc_ref_psets]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-staging_ifc_ref_psets] (
  [pset_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_staging_ifc_ref_psets] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [name] NVARCHAR(255) NOT NULL,  -- IFC pset name
  CONSTRAINT [FK_cpd_ifc_psets_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE CASCADE
);
GO

IF OBJECT_ID(N'[dbo].[cpd-staging_ifc_ref_dtypes]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-staging_ifc_ref_dtypes] (
  [dtype_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_staging_ifc_ref_dtypes] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [name] NVARCHAR(255) NOT NULL,  -- Discovered/source datatype label
  CONSTRAINT [FK_cpd_ifc_dtypes_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE CASCADE
);
GO

IF OBJECT_ID(N'[dbo].[cpd-staging_ifc_ref_units]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-staging_ifc_ref_units] (
  [unit_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_staging_ifc_ref_units] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [name] NVARCHAR(255) NOT NULL,  -- Unit name (e.g., meter)
  [symbol] NVARCHAR(50) NULL,     -- Unit symbol (e.g., m)
  CONSTRAINT [FK_cpd_ifc_units_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE CASCADE
);
GO

IF OBJECT_ID(N'[dbo].[cpd-staging_ifc_ref_types]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-staging_ifc_ref_types] (
  [type_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_staging_ifc_ref_types] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [name] NVARCHAR(255) NOT NULL,  -- IFC class/type label
  CONSTRAINT [FK_cpd_ifc_types_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE CASCADE
);
GO

IF OBJECT_ID(N'[dbo].[cpd-staging_ifc_ref_attrs]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-staging_ifc_ref_attrs] (
  [attr_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_staging_ifc_ref_attrs] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [pset_id] INT NOT NULL,
  [name] NVARCHAR(255) NOT NULL,  -- Attribute/property name
  [dtype_id] INT NULL,            -- Suggested type
  [unit_id] INT NULL,             -- Suggested unit
  CONSTRAINT [FK_cpd_ifc_attrs_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE NO ACTION,
  CONSTRAINT [FK_cpd_ifc_attrs_pset]
    FOREIGN KEY ([pset_id]) REFERENCES [dbo].[cpd-staging_ifc_ref_psets]([pset_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_ifc_attrs_dtype]
    FOREIGN KEY ([dtype_id]) REFERENCES [dbo].[cpd-staging_ifc_ref_dtypes]([dtype_id]) ON DELETE NO ACTION,
  CONSTRAINT [FK_cpd_ifc_attrs_unit]
    FOREIGN KEY ([unit_id]) REFERENCES [dbo].[cpd-staging_ifc_ref_units]([unit_id]) ON DELETE NO ACTION
);
GO

IF OBJECT_ID(N'[dbo].[cpd-staging_ifc_elements]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-staging_ifc_elements] (
  [element_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_staging_ifc_elements] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [ifc_guid] NVARCHAR(64) NOT NULL,  -- Stable IFC GUID
  [ifc_class] NVARCHAR(128) NOT NULL,-- IFC entity class (e.g., IfcWall)
  [name] NVARCHAR(255) NULL,
  [parent_guid] NVARCHAR(64) NULL,   -- Parent relationship by GUID if available
  [type_id] INT NULL,                -- FK to ref_types
  [raw_json] NVARCHAR(MAX) NULL,     -- Raw source payload for diagnostics
  CONSTRAINT [FK_cpd_ifc_elements_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_ifc_elements_type]
    FOREIGN KEY ([type_id]) REFERENCES [dbo].[cpd-staging_ifc_ref_types]([type_id]) ON DELETE NO ACTION
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_cpd_ifc_elements_ifc_guid' AND object_id = OBJECT_ID(N'[dbo].[cpd-staging_ifc_elements]'))
CREATE INDEX [IX_cpd_ifc_elements_ifc_guid] ON [dbo].[cpd-staging_ifc_elements]([ifc_guid]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_cpd_ifc_elements_ifc_class' AND object_id = OBJECT_ID(N'[dbo].[cpd-staging_ifc_elements]'))
CREATE INDEX [IX_cpd_ifc_elements_ifc_class] ON [dbo].[cpd-staging_ifc_elements]([ifc_class]);
GO

IF OBJECT_ID(N'[dbo].[cpd-staging_ifc_propvals]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-staging_ifc_propvals] (
  [propval_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_staging_ifc_propvals] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [element_id] INT NOT NULL,
  [attr_id] INT NOT NULL,
  [dtype_id] INT NULL,    -- Optional override/specific dtype
  [unit_id] INT NULL,     -- Optional override/specific unit

  -- Value slots (nullable)
  [v_text] NVARCHAR(MAX) NULL,   -- Textual value
  [v_num] FLOAT NULL,            -- Floating numeric value
  [v_int] INT NULL,              -- Integer value
  [v_bool] BIT NULL,             -- Boolean
  [v_json] NVARCHAR(MAX) NULL,   -- Structured value (JSON)
  [v_date] DATE NULL,            -- Date value
  [v_datetime] DATETIME2(3) NULL,-- Datetime value

  [raw_json] NVARCHAR(MAX) NULL, -- Original raw field/value

  CONSTRAINT [FK_cpd_ifc_propvals_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE NO ACTION,
  CONSTRAINT [FK_cpd_ifc_propvals_element]
    FOREIGN KEY ([element_id]) REFERENCES [dbo].[cpd-staging_ifc_elements]([element_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_ifc_propvals_attr]
    FOREIGN KEY ([attr_id]) REFERENCES [dbo].[cpd-staging_ifc_ref_attrs]([attr_id]) ON DELETE NO ACTION,
  CONSTRAINT [FK_cpd_ifc_propvals_dtype]
    FOREIGN KEY ([dtype_id]) REFERENCES [dbo].[cpd-staging_ifc_ref_dtypes]([dtype_id]) ON DELETE NO ACTION,
  CONSTRAINT [FK_cpd_ifc_propvals_unit]
    FOREIGN KEY ([unit_id]) REFERENCES [dbo].[cpd-staging_ifc_ref_units]([unit_id]) ON DELETE NO ACTION
);
GO

---------------------------------------------------------------
-- Canonical Dictionary
---------------------------------------------------------------
IF OBJECT_ID(N'[dbo].[cpd-canonical_psets]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-canonical_psets] (
  [pset_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_canonical_psets] PRIMARY KEY,
  [name] NVARCHAR(255) NOT NULL CONSTRAINT [UQ_cpd_canonical_psets_name] UNIQUE, -- Canonical pset name
  [created_at] DATETIME2(3) NULL,
  [created_by] NVARCHAR(255) NULL,
  [updated_at] DATETIME2(3) NULL,
  [updated_by] NVARCHAR(255) NULL
);
GO

IF OBJECT_ID(N'[dbo].[cpd-canonical_units]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-canonical_units] (
  [unit_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_canonical_units] PRIMARY KEY,
  [name] NVARCHAR(255) NOT NULL CONSTRAINT [UQ_cpd_canonical_units_name] UNIQUE,
  [symbol] NVARCHAR(50) NULL,
  [created_at] DATETIME2(3) NULL,
  [created_by] NVARCHAR(255) NULL,
  [updated_at] DATETIME2(3) NULL,
  [updated_by] NVARCHAR(255) NULL
);
GO

IF OBJECT_ID(N'[dbo].[cpd-canonical_datatypes]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-canonical_datatypes] (
  [type_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_canonical_datatypes] PRIMARY KEY,
  [name] NVARCHAR(255) NOT NULL CONSTRAINT [UQ_cpd_canonical_datatypes_name] UNIQUE,
  [created_at] DATETIME2(3) NULL,
  [created_by] NVARCHAR(255) NULL,
  [updated_at] DATETIME2(3) NULL,
  [updated_by] NVARCHAR(255) NULL
);
GO

IF OBJECT_ID(N'[dbo].[cpd-canonical_value_domains]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-canonical_value_domains] (
  [domain_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_canonical_value_domains] PRIMARY KEY,
  [name] NVARCHAR(255) NOT NULL CONSTRAINT [UQ_cpd_canonical_value_domains_name] UNIQUE,
  [created_at] DATETIME2(3) NULL,
  [created_by] NVARCHAR(255) NULL,
  [updated_at] DATETIME2(3) NULL,
  [updated_by] NVARCHAR(255) NULL
);
GO

IF OBJECT_ID(N'[dbo].[cpd-canonical_value_items]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-canonical_value_items] (
  [item_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_canonical_value_items] PRIMARY KEY,
  [domain_id] INT NOT NULL,
  [code] NVARCHAR(255) NOT NULL,    -- Machine code
  [label] NVARCHAR(255) NULL,       -- Human label
  [created_at] DATETIME2(3) NULL,
  [created_by] NVARCHAR(255) NULL,
  [updated_at] DATETIME2(3) NULL,
  [updated_by] NVARCHAR(255) NULL,
  CONSTRAINT [FK_cpd_canonical_value_items_domain]
    FOREIGN KEY ([domain_id]) REFERENCES [dbo].[cpd-canonical_value_domains]([domain_id]) ON DELETE CASCADE
);
GO

IF OBJECT_ID(N'[dbo].[cpd-canonical_attributes]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-canonical_attributes] (
  [attr_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_canonical_attributes] PRIMARY KEY,
  [pset_id] INT NOT NULL,
  [name] NVARCHAR(255) NOT NULL,
  [datatype] NVARCHAR(128) NULL,   -- Free-form datatype label
  [unit_id] INT NULL,
  [value_domain_id] INT NULL,
  [created_at] DATETIME2(3) NULL,
  [created_by] NVARCHAR(255) NULL,
  [updated_at] DATETIME2(3) NULL,
  [updated_by] NVARCHAR(255) NULL,
  CONSTRAINT [FK_cpd_canonical_attributes_pset]
    FOREIGN KEY ([pset_id]) REFERENCES [dbo].[cpd-canonical_psets]([pset_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_canonical_attributes_unit]
    FOREIGN KEY ([unit_id]) REFERENCES [dbo].[cpd-canonical_units]([unit_id]) ON DELETE SET NULL,
  CONSTRAINT [FK_cpd_canonical_attributes_domain]
    FOREIGN KEY ([value_domain_id]) REFERENCES [dbo].[cpd-canonical_value_domains]([domain_id]) ON DELETE SET NULL
);
GO

---------------------------------------------------------------
-- Mappings (per-version alignment of source -> canonical)
---------------------------------------------------------------
IF OBJECT_ID(N'[dbo].[cpd-map_ifc_psets]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-map_ifc_psets] (
  [mapping_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_map_ifc_psets] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [src_pset] NVARCHAR(255) NOT NULL,
  [canonical_pset_id] INT NOT NULL,
  CONSTRAINT [FK_cpd_map_ifc_psets_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_map_ifc_psets_cps]
    FOREIGN KEY ([canonical_pset_id]) REFERENCES [dbo].[cpd-canonical_psets]([pset_id]) ON DELETE CASCADE
);
GO

IF OBJECT_ID(N'[dbo].[cpd-map_ifc_attrs]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-map_ifc_attrs] (
  [mapping_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_map_ifc_attrs] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [src_pset] NVARCHAR(255) NOT NULL,
  [src_attr] NVARCHAR(255) NOT NULL,
  [canonical_attr_id] INT NOT NULL,
  CONSTRAINT [FK_cpd_map_ifc_attrs_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_map_ifc_attrs_cattr]
    FOREIGN KEY ([canonical_attr_id]) REFERENCES [dbo].[cpd-canonical_attributes]([attr_id]) ON DELETE CASCADE
);
GO

IF OBJECT_ID(N'[dbo].[cpd-map_ifc_units]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-map_ifc_units] (
  [mapping_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_map_ifc_units] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [src_unit] NVARCHAR(255) NOT NULL,
  [canonical_unit_id] INT NOT NULL,
  CONSTRAINT [FK_cpd_map_ifc_units_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_map_ifc_units_cunit]
    FOREIGN KEY ([canonical_unit_id]) REFERENCES [dbo].[cpd-canonical_units]([unit_id]) ON DELETE CASCADE
);
GO

IF OBJECT_ID(N'[dbo].[cpd-map_ifc_types]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-map_ifc_types] (
  [mapping_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_map_ifc_types] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [src_type] NVARCHAR(255) NOT NULL,
  [canonical_type_id] INT NOT NULL,
  CONSTRAINT [FK_cpd_map_ifc_types_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_map_ifc_types_ctype]
    FOREIGN KEY ([canonical_type_id]) REFERENCES [dbo].[cpd-canonical_datatypes]([type_id]) ON DELETE CASCADE
);
GO

IF OBJECT_ID(N'[dbo].[cpd-map_ifc_values]', N'U') IS NULL
CREATE TABLE [dbo].[cpd-map_ifc_values] (
  [mapping_id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_cpd_map_ifc_values] PRIMARY KEY,
  [version_id] INT NOT NULL,
  [canonical_attr_id] INT NOT NULL,
  [src_value] NVARCHAR(4000) NOT NULL,
  [canonical_value_item_id] INT NOT NULL,
  CONSTRAINT [FK_cpd_map_ifc_values_version]
    FOREIGN KEY ([version_id]) REFERENCES [dbo].[cpd-source_versions]([version_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_map_ifc_values_cattr]
    FOREIGN KEY ([canonical_attr_id]) REFERENCES [dbo].[cpd-canonical_attributes]([attr_id]) ON DELETE CASCADE,
  CONSTRAINT [FK_cpd_map_ifc_values_citem]
    FOREIGN KEY ([canonical_value_item_id]) REFERENCES [dbo].[cpd-canonical_value_items]([item_id]) ON DELETE CASCADE
);
GO
