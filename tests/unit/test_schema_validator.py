import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from contextlib import contextmanager

from src.services.schema_validator import SchemaValidator, SchemaValidationResult, TableSchema


def create_mock_gateway():
    """Create a properly mocked gateway with transaction support"""
    mock_gateway = Mock()

    @contextmanager
    def mock_transaction():
        yield

    mock_gateway.transaction = mock_transaction
    return mock_gateway


def test_schema_validator_initialization():
    """Test that SchemaValidator can be initialized with a gateway"""
    mock_gateway = Mock()
    
    # Mock the azure.sql file existence
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="-- Mock azure.sql content"):
        validator = SchemaValidator(mock_gateway)
        assert validator.gateway == mock_gateway


def test_parse_table_definition():
    """Test parsing of table definition from azure.sql"""
    mock_gateway = Mock()
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="-- Mock content"):
        validator = SchemaValidator(mock_gateway)
    
    # Test parsing a simple table definition
    table_def = """
    [id] INT NOT NULL IDENTITY(1,1) CONSTRAINT [PK_test] PRIMARY KEY,
    [name] NVARCHAR(255) NOT NULL,
    [value] NVARCHAR(4000) NOT NULL
    """
    
    schema = validator._parse_table_definition("test_table", table_def)
    
    assert schema.name == "test_table"
    assert "id" in schema.columns
    assert "name" in schema.columns
    assert "value" in schema.columns
    assert schema.columns["id"] == "INT"
    assert schema.columns["name"] == "NVARCHAR(255)"
    assert schema.columns["value"] == "NVARCHAR(4000)"


def test_validation_result_no_tables():
    """Test validation result when remote database has no tables"""
    mock_gateway = create_mock_gateway()
    mock_gateway.query_all.return_value = []  # No tables

    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="""
         CREATE TABLE [dbo].[cpd-test_table] (
             [id] INT NOT NULL CONSTRAINT [PK_cpd_test] PRIMARY KEY
         );
         """):
        validator = SchemaValidator(mock_gateway)
        result = validator.validate_schema()

    assert not result.is_valid
    assert result.has_no_tables
    assert len(result.missing_tables) > 0


def test_validation_result_valid_schema():
    """Test validation result when schema matches perfectly"""
    mock_gateway = create_mock_gateway()

    # Mock existing tables query
    mock_gateway.query_all.side_effect = [
        [("cpd-test_table",)],  # Table names
        [("id", "INT", None, None, None)],  # Columns for cpd-test_table
        [("id",)],  # Primary key
        []  # Foreign keys
    ]

    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="""
         CREATE TABLE [dbo].[cpd-test_table] (
             [id] INT NOT NULL CONSTRAINT [PK_cpd_test_table] PRIMARY KEY
         );
         """):
        validator = SchemaValidator(mock_gateway)
        result = validator.validate_schema()

    assert result.is_valid
    assert not result.has_no_tables
    assert len(result.missing_tables) == 0
    assert len(result.extra_tables) == 0
    assert len(result.table_deviations) == 0


def test_validation_result_missing_tables():
    """Test validation result when tables are missing"""
    mock_gateway = create_mock_gateway()

    # Mock existing tables query - return empty (no tables exist)
    mock_gateway.query_all.side_effect = [
        [],  # No tables exist
    ]

    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="""
         CREATE TABLE [dbo].[cpd-expected_table] (
             [id] INT NOT NULL CONSTRAINT [PK_cpd_expected_table] PRIMARY KEY
         );
         """):
        validator = SchemaValidator(mock_gateway)
        result = validator.validate_schema()

    assert not result.is_valid
    assert result.has_no_tables
    assert "cpd-expected_table" in result.missing_tables


def test_validation_result_extra_tables():
    """Test validation result when extra tables exist"""
    mock_gateway = create_mock_gateway()

    # Mock existing tables query - return extra table
    mock_gateway.query_all.side_effect = [
        [("cpd-extra_table",)],  # Extra table exists
        [("id", "INT", None, None, None)],  # Columns for cpd-extra_table
        [("id",)],  # Primary key
        []  # Foreign keys
    ]

    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="-- No CREATE TABLE statements"):
        validator = SchemaValidator(mock_gateway)
        result = validator.validate_schema()

    assert not result.is_valid
    assert not result.has_no_tables
    assert "cpd-extra_table" in result.extra_tables


def test_validation_handles_errors():
    """Test that validation handles database errors gracefully"""
    mock_gateway = create_mock_gateway()
    mock_gateway.query_all.side_effect = Exception("Database connection failed")

    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="-- Mock content"):
        validator = SchemaValidator(mock_gateway)
        result = validator.validate_schema()

    assert not result.is_valid
    assert result.error_message is not None
    assert "Database connection failed" in result.error_message


def test_deploy_schema():
    """Test schema deployment functionality"""
    mock_gateway = Mock()
    
    mock_sql_content = """
    -- Test comment
    CREATE TABLE [dbo].[test_table] (
        [id] INT NOT NULL
    );
    GO
    
    CREATE TABLE [dbo].[another_table] (
        [name] NVARCHAR(255)
    );
    GO
    """
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value=mock_sql_content):
        validator = SchemaValidator(mock_gateway)
        validator.deploy_schema()
    
    # Verify that execute was called for each statement
    assert mock_gateway.execute.call_count >= 2  # At least 2 CREATE TABLE statements
