"""
Integration tests for schema validation during project loading.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.services.app_context import AppContext
from src.services.database_gateway import DatabaseError


def test_schema_validation_during_project_loading():
    """Test that schema validation is triggered during remote project loading"""

    # Create a mock project file
    mock_project_path = Path("test_remote.sqlite")

    # Mock MSSQL gateway
    mock_mssql_gateway = Mock()
    mock_mssql_gateway.init = Mock()
    mock_mssql_gateway.health_check = Mock()

    # Mock schema validator
    mock_validator = Mock()
    mock_validation_result = Mock()
    mock_validation_result.is_valid = False
    mock_validation_result.has_no_tables = True
    mock_validation_result.error_message = None
    mock_validator.validate_schema.return_value = mock_validation_result

    with patch('pathlib.Path.exists', return_value=True), \
         patch('src.services.app_context.AppContext._read_storage_mode', return_value="mssql"), \
         patch('src.services.app_context.AppContext._read_remote_descriptor',
               return_value=("test-server", "test-db", "windows", None, None, 30)), \
         patch('src.services.db_adapters.mssql_adapter.MssqlAdapter', return_value=mock_mssql_gateway), \
         patch('src.services.schema_validator.SchemaValidator', return_value=mock_validator):

        app_context = AppContext()

        # This should raise a schema validation error
        with pytest.raises(DatabaseError) as exc_info:
            app_context.load_project(str(mock_project_path))

        assert str(exc_info.value) == "SCHEMA_DEPLOYMENT_REQUIRED"

        # Verify that schema validation was attempted
        mock_validator.validate_schema.assert_called_once()

        # Verify that pending validation data is stored
        pending = app_context.get_pending_schema_validation()
        assert pending is not None
        assert pending['result'] == mock_validation_result


def test_schema_validation_success_continues_loading():
    """Test that successful schema validation allows project loading to continue"""

    # Create a mock project file
    mock_project_path = Path("test_remote.sqlite")

    # Mock MSSQL gateway
    mock_mssql_gateway = Mock()
    mock_mssql_gateway.init = Mock()
    mock_mssql_gateway.health_check = Mock()

    # Mock schema validator with successful validation
    mock_validator = Mock()
    mock_validation_result = Mock()
    mock_validation_result.is_valid = True
    mock_validation_result.has_no_tables = False
    mock_validation_result.error_message = None
    mock_validator.validate_schema.return_value = mock_validation_result

    with patch('pathlib.Path.exists', return_value=True), \
         patch('src.services.app_context.AppContext._read_storage_mode', return_value="mssql"), \
         patch('src.services.app_context.AppContext._read_remote_descriptor',
               return_value=("test-server", "test-db", "windows", None, None, 30)), \
         patch('src.services.db_adapters.mssql_adapter.MssqlAdapter', return_value=mock_mssql_gateway), \
         patch('src.services.schema_validator.SchemaValidator', return_value=mock_validator), \
         patch('builtins.print') as mock_print:  # Mock print to capture log message

        app_context = AppContext()

        # This should succeed without raising an exception
        app_context.load_project(str(mock_project_path))

        # Verify that schema validation was attempted
        mock_validator.validate_schema.assert_called_once()

        # Verify success log message
        mock_print.assert_called_with("INFO: Schema validation successful for remote database")

        # Verify that no pending validation data is stored
        pending = app_context.get_pending_schema_validation()
        assert pending is None

        # Verify that the gateway was set
        assert app_context.gateway == mock_mssql_gateway


def test_schema_validation_error_handling():
    """Test that schema validation errors are properly handled"""

    # Create a mock project file
    mock_project_path = Path("test_remote.sqlite")

    # Mock MSSQL gateway
    mock_mssql_gateway = Mock()
    mock_mssql_gateway.init = Mock()
    mock_mssql_gateway.health_check = Mock()

    # Mock schema validator with error
    mock_validator = Mock()
    mock_validation_result = Mock()
    mock_validation_result.is_valid = False
    mock_validation_result.has_no_tables = False
    mock_validation_result.error_message = "Database connection failed"
    mock_validator.validate_schema.return_value = mock_validation_result

    with patch('pathlib.Path.exists', return_value=True), \
         patch('src.services.app_context.AppContext._read_storage_mode', return_value="mssql"), \
         patch('src.services.app_context.AppContext._read_remote_descriptor',
               return_value=("test-server", "test-db", "windows", None, None, 30)), \
         patch('src.services.db_adapters.mssql_adapter.MssqlAdapter', return_value=mock_mssql_gateway), \
         patch('src.services.schema_validator.SchemaValidator', return_value=mock_validator):

        app_context = AppContext()

        # This should raise a schema validation error with the specific message
        with pytest.raises(DatabaseError) as exc_info:
            app_context.load_project(str(mock_project_path))

        assert "Schema validation error: Database connection failed" in str(exc_info.value)


def test_schema_deployment_functionality():
    """Test that schema deployment works correctly"""
    
    app_context = AppContext()
    
    # Mock pending validation data
    mock_validator = Mock()
    mock_result = Mock()
    app_context._pending_schema_validation = {
        'validator': mock_validator,
        'result': mock_result,
        'project_path': 'test.sqlite'
    }
    
    # Call schema deployment
    app_context.handle_schema_deployment()
    
    # Verify that deploy_schema was called
    mock_validator.deploy_schema.assert_called_once()
    
    # Verify that pending validation was cleared
    assert app_context.get_pending_schema_validation() is None


def test_schema_deployment_without_pending_data():
    """Test that schema deployment fails without pending validation data"""
    
    app_context = AppContext()
    
    # Try to deploy schema without pending validation data
    with pytest.raises(ValueError) as exc_info:
        app_context.handle_schema_deployment()
    
    assert "No pending schema validation" in str(exc_info.value)
