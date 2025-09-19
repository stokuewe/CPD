-- Baseline migration establishing settings schema for version 1.0.0
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mssql_connection (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    server TEXT NOT NULL,
    database TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 1433,
    auth_type TEXT NOT NULL CHECK (auth_type IN ('sql', 'windows')),
    username TEXT,
    password TEXT
);

INSERT INTO meta (key, value)
VALUES ('schema_version', '1.0.0')
ON CONFLICT(key) DO UPDATE SET value = excluded.value;
