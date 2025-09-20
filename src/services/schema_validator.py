"""
Schema validation service for remote MSSQL databases.
Validates that the remote database schema matches azure.sql requirements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.services.database_gateway import DatabaseGateway


@dataclass
class TableSchema:
    """Represents expected table schema from azure.sql"""
    name: str
    columns: Dict[str, str]  # column_name -> data_type
    primary_key: Optional[str] = None
    foreign_keys: List[Tuple[str, str, str]] = None  # (column, ref_table, ref_column)
    constraints: List[str] = None

    def __post_init__(self):
        if self.foreign_keys is None:
            self.foreign_keys = []
        if self.constraints is None:
            self.constraints = []


@dataclass
class SchemaValidationResult:
    """Result of schema validation"""
    is_valid: bool
    missing_tables: List[str]
    extra_tables: List[str]
    table_deviations: Dict[str, List[str]]  # table_name -> list of issues
    has_no_tables: bool = False
    error_message: Optional[str] = None


class SchemaValidator:
    """Validates remote MSSQL database schema against azure.sql"""

    def __init__(self, gateway: DatabaseGateway):
        self.gateway = gateway
        self._expected_schema = self._load_expected_schema()

    def _load_expected_schema(self) -> Dict[str, TableSchema]:
        """Parse azure.sql to extract expected schema"""
        repo_root = Path(__file__).resolve().parents[2]
        azure_sql_path = repo_root / "azure.sql"
        
        if not azure_sql_path.exists():
            raise FileNotFoundError(f"azure.sql not found at {azure_sql_path}")
        
        sql_content = azure_sql_path.read_text(encoding="utf-8")
        return self._parse_azure_sql(sql_content)

    def _parse_azure_sql(self, sql_content: str) -> Dict[str, TableSchema]:
        """Parse azure.sql content to extract table schemas"""
        schemas = {}
        
        # Remove comments and normalize whitespace
        sql_content = re.sub(r'--.*$', '', sql_content, flags=re.MULTILINE)
        sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
        
        # Find CREATE TABLE statements (with cpd- prefix)
        create_table_pattern = r'CREATE TABLE \[dbo\]\.\[(cpd-[\w-]+)\]\s*\((.*?)\);'
        
        for match in re.finditer(create_table_pattern, sql_content, re.DOTALL | re.IGNORECASE):
            table_name = match.group(1)
            table_def = match.group(2)
            
            schema = self._parse_table_definition(table_name, table_def)
            schemas[table_name] = schema
        
        return schemas

    def _parse_table_definition(self, table_name: str, table_def: str) -> TableSchema:
        """Parse individual table definition"""
        columns = {}
        primary_key = None
        foreign_keys = []
        constraints = []
        
        # Split by commas, but be careful with nested parentheses
        lines = []
        current_line = ""
        paren_count = 0
        
        for char in table_def:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                lines.append(current_line.strip())
                current_line = ""
                continue
            current_line += char
        
        if current_line.strip():
            lines.append(current_line.strip())
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Column definition - handle both simple and complex column definitions
            if line.startswith('['):
                # Extract column name and type, handling CONSTRAINT clauses
                col_match = re.match(r'\[(\w+)\]\s+(\w+(?:\(\d+(?:,\d+)?\))?)', line)
                if col_match:
                    col_name = col_match.group(1)
                    col_type = col_match.group(2)
                    columns[col_name] = col_type

                    # Check if this line also contains a PRIMARY KEY constraint
                    if 'PRIMARY KEY' in line.upper():
                        primary_key = col_name
            
            # Primary key constraint (standalone)
            elif 'PRIMARY KEY' in line.upper() and 'CONSTRAINT' in line.upper():
                # This handles standalone CONSTRAINT lines
                pk_match = re.search(r'CONSTRAINT \[PK_\w+\] PRIMARY KEY', line)
                if pk_match:
                    # Extract column name from the line context
                    if '[' in line and ']' in line:
                        col_match = re.search(r'\[(\w+)\]', line)
                        if col_match:
                            primary_key = col_match.group(1)
            
            # Foreign key constraint
            elif 'FOREIGN KEY' in line.upper():
                fk_match = re.search(r'FOREIGN KEY \(\[(\w+)\]\) REFERENCES \[dbo\]\.\[(\w+)\]\(\[(\w+)\]\)', line)
                if fk_match:
                    col_name, ref_table, ref_col = fk_match.groups()
                    foreign_keys.append((col_name, ref_table, ref_col))
        
        return TableSchema(
            name=table_name,
            columns=columns,
            primary_key=primary_key,
            foreign_keys=foreign_keys,
            constraints=constraints
        )

    def validate_schema(self) -> SchemaValidationResult:
        """Validate remote database schema against azure.sql"""
        try:
            # Get existing tables from remote database
            existing_tables = self._get_existing_tables()
            
            if not existing_tables:
                return SchemaValidationResult(
                    is_valid=False,
                    missing_tables=list(self._expected_schema.keys()),
                    extra_tables=[],
                    table_deviations={},
                    has_no_tables=True
                )
            
            # Compare schemas
            missing_tables = []
            extra_tables = []
            table_deviations = {}
            
            expected_table_names = set(self._expected_schema.keys())
            existing_table_names = set(existing_tables.keys())
            
            missing_tables = list(expected_table_names - existing_table_names)
            extra_tables = list(existing_table_names - expected_table_names)
            
            # Check existing tables for deviations
            for table_name in expected_table_names & existing_table_names:
                deviations = self._compare_table_schema(
                    table_name,
                    self._expected_schema[table_name],
                    existing_tables[table_name]
                )
                if deviations:
                    table_deviations[table_name] = deviations
            
            is_valid = not missing_tables and not extra_tables and not table_deviations
            
            return SchemaValidationResult(
                is_valid=is_valid,
                missing_tables=missing_tables,
                extra_tables=extra_tables,
                table_deviations=table_deviations
            )
            
        except Exception as e:
            return SchemaValidationResult(
                is_valid=False,
                missing_tables=[],
                extra_tables=[],
                table_deviations={},
                error_message=str(e)
            )

    def _get_existing_tables(self) -> Dict[str, Dict[str, Any]]:
        """Get existing table schemas from remote database"""
        tables = {}

        # Use a transaction to reuse a single connection for all queries
        with self.gateway.transaction():
            # Get table names with cpd- prefix, excluding system tables
            table_query = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo'
                AND TABLE_TYPE = 'BASE TABLE'
                AND TABLE_NAME LIKE 'cpd-%'
                AND TABLE_NAME NOT IN ('sysdiagrams', 'dtproperties')
            """

            table_rows = self.gateway.query_all(table_query)
            if not table_rows:
                return tables

            for table_name, in table_rows:
                # Get column information
                column_query = """
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
                """

                columns = {}
                column_rows = self.gateway.query_all(column_query, (table_name,))

                for col_name, data_type, max_length, precision, scale in column_rows:
                    # Reconstruct type string similar to azure.sql format
                    if data_type.upper() in ('NVARCHAR', 'VARCHAR', 'CHAR', 'NCHAR'):
                        if max_length and max_length != -1:
                            type_str = f"{data_type.upper()}({max_length})"
                        else:
                            type_str = f"{data_type.upper()}(MAX)"
                    elif data_type.upper() in ('DECIMAL', 'NUMERIC'):
                        if precision and scale:
                            type_str = f"{data_type.upper()}({precision},{scale})"
                        else:
                            type_str = data_type.upper()
                    else:
                        type_str = data_type.upper()

                    columns[col_name] = type_str

                # Get primary key column for this table
                pk_query = """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
                AND CONSTRAINT_NAME LIKE 'PK_%'
                """
                pk_rows = self.gateway.query_all(pk_query, (table_name,))
                primary_key = pk_rows[0][0] if pk_rows else None

                # Get foreign key constraints for this table
                fk_query = """
                SELECT
                    kcu.COLUMN_NAME,
                    kcu2.TABLE_NAME AS REFERENCED_TABLE,
                    kcu2.COLUMN_NAME AS REFERENCED_COLUMN
                FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                    ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu2
                    ON rc.UNIQUE_CONSTRAINT_NAME = kcu2.CONSTRAINT_NAME
                WHERE kcu.TABLE_SCHEMA = 'dbo' AND kcu.TABLE_NAME = ?
                """
                fk_rows = self.gateway.query_all(fk_query, (table_name,))
                foreign_keys = [(col, ref_table, ref_col) for col, ref_table, ref_col in fk_rows]

                tables[table_name] = {
                    'columns': columns,
                    'primary_key': primary_key,
                    'foreign_keys': foreign_keys
                }

            return tables

    def _compare_table_schema(self, table_name: str, expected: TableSchema, existing: Dict[str, Any]) -> List[str]:
        """Compare expected vs existing table schema"""
        deviations = []
        
        expected_cols = set(expected.columns.keys())
        existing_cols = set(existing['columns'].keys())
        
        missing_cols = expected_cols - existing_cols
        extra_cols = existing_cols - expected_cols
        
        if missing_cols:
            deviations.append(f"Missing columns: {', '.join(missing_cols)}")
        
        if extra_cols:
            deviations.append(f"Extra columns: {', '.join(extra_cols)}")
        
        # Check column types for common columns
        for col_name in expected_cols & existing_cols:
            expected_type = expected.columns[col_name].upper()
            existing_type = existing['columns'][col_name].upper()

            if not self._are_types_compatible(expected_type, existing_type):
                deviations.append(f"Column '{col_name}': expected {expected_type}, found {existing_type}")
        
        # Check primary key
        if expected.primary_key != existing.get('primary_key'):
            deviations.append(f"Primary key mismatch: expected {expected.primary_key}, found {existing.get('primary_key')}")
        
        return deviations

    def _are_types_compatible(self, expected_type: str, existing_type: str) -> bool:
        """Check if two SQL Server data types are functionally compatible"""
        # Exact match
        if expected_type == existing_type:
            return True

        # DATETIME2(3) vs DATETIME2 - both store datetime with millisecond precision
        if (expected_type == 'DATETIME2(3)' and existing_type == 'DATETIME2') or \
           (expected_type == 'DATETIME2' and existing_type == 'DATETIME2(3)'):
            return True

        # NVARCHAR vs NVARCHAR(MAX) - MAX is more flexible and compatible
        if (expected_type == 'NVARCHAR' and existing_type == 'NVARCHAR(MAX)') or \
           (expected_type == 'NVARCHAR(MAX)' and existing_type == 'NVARCHAR'):
            return True

        # VARCHAR vs VARCHAR(MAX) - same logic
        if (expected_type == 'VARCHAR' and existing_type == 'VARCHAR(MAX)') or \
           (expected_type == 'VARCHAR(MAX)' and existing_type == 'VARCHAR'):
            return True

        return False

    def deploy_schema(self) -> None:
        """Deploy azure.sql schema to remote database"""
        repo_root = Path(__file__).resolve().parents[2]
        azure_sql_path = repo_root / "azure.sql"
        
        if not azure_sql_path.exists():
            raise FileNotFoundError(f"azure.sql not found at {azure_sql_path}")
        
        sql_content = azure_sql_path.read_text(encoding="utf-8")
        
        # Split into individual statements and execute
        statements = self._split_sql_statements(sql_content)
        
        for statement in statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                self.gateway.execute(statement)

    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements"""
        # Remove comments
        sql_content = re.sub(r'--.*$', '', sql_content, flags=re.MULTILINE)
        
        # Split by GO statements (SQL Server batch separator)
        statements = []
        current_statement = ""
        
        for line in sql_content.split('\n'):
            line = line.strip()
            if line.upper() == 'GO':
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
            else:
                current_statement += line + '\n'
        
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
