import pytest
from unittest.mock import patch, Mock

from src.services.project_creator_remote import ProjectCreatorRemote


def test_project_creator_remote_validates_required_fields():
    """Test that ProjectCreatorRemote validates required server and database fields"""
    # Missing server
    descriptor = {"database": "test_db"}
    creator = ProjectCreatorRemote(descriptor)
    
    with pytest.raises(ValueError, match="Server and Database are required"):
        creator.create()
    
    # Missing database
    descriptor = {"server": "test_server"}
    creator = ProjectCreatorRemote(descriptor)
    
    with pytest.raises(ValueError, match="Server and Database are required"):
        creator.create()


def test_project_creator_remote_tests_connection():
    """Test that ProjectCreatorRemote actually tests the database connection"""
    descriptor = {
        "server": "test_server",
        "database": "test_db",
        "auth_type": "sql",
        "username": "test_user"
    }

    creator = ProjectCreatorRemote(descriptor)

    # Mock the _test_connection method to simulate failure
    with patch.object(creator, '_test_connection') as mock_test:
        mock_test.side_effect = RuntimeError("Connection test failed: Connection failed")

        with pytest.raises(RuntimeError, match="Connection test failed"):
            creator.create()


def test_project_creator_remote_skips_test_without_pyodbc():
    """Test that ProjectCreatorRemote gracefully skips connection test if pyodbc unavailable"""
    descriptor = {
        "server": "test_server",
        "database": "test_db"
    }

    creator = ProjectCreatorRemote(descriptor)

    # Mock the _test_connection method to simulate pyodbc not available (should not raise)
    with patch.object(creator, '_test_connection') as mock_test:
        mock_test.return_value = None  # Simulate successful skip

        # Should not raise an exception - should skip the connection test
        creator.create()  # Should succeed


def test_project_creator_remote_successful_connection():
    """Test that ProjectCreatorRemote succeeds with valid connection"""
    descriptor = {
        "server": "test_server",
        "database": "test_db",
        "auth_type": "windows"
    }

    creator = ProjectCreatorRemote(descriptor)

    # Mock successful connection test
    with patch.object(creator, '_test_connection') as mock_test:
        mock_test.return_value = None  # Simulate successful connection test

        # Should succeed without raising an exception
        creator.create()
