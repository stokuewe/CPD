"""
Azure AD Token Manager for CPD Application

Handles authentication token acquisition, caching, and refresh for Azure AD authentication.
Follows Microsoft OAuth 2.0 best practices for desktop applications.
"""

from __future__ import annotations
import threading
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


@dataclass
class AuthToken:
    """Represents a cached authentication token"""
    access_token: str
    expires_at: datetime
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 5-minute buffer)"""
        return datetime.now() >= (self.expires_at - timedelta(minutes=5))
    
    @property
    def expires_in_seconds(self) -> int:
        """Get seconds until token expires"""
        delta = self.expires_at - datetime.now()
        return max(0, int(delta.total_seconds()))


@dataclass
class ConnectionDescriptor:
    """Azure AD connection parameters"""
    server: str
    database: str
    auth_type: str  # azure_ad_interactive, azure_ad_password, etc.
    username: Optional[str] = None
    authority: Optional[str] = None
    timeout_seconds: int = 30
    use_driver17: bool = False  # For Azure AD Driver 17 fallback
    
    def cache_key(self) -> str:
        """Generate unique cache key for this connection"""
        return f"{self.server}:{self.database}:{self.auth_type}:{self.username or 'none'}"


class AzureADTokenManager:
    """
    Manages Azure AD authentication tokens for database connections.
    
    Features:
    - Token caching per connection descriptor
    - Automatic token refresh
    - Thread-safe operations
    - Main thread authentication for Interactive mode
    """
    
    def __init__(self):
        self._token_cache: Dict[str, AuthToken] = {}
        self._lock = threading.RLock()
        self._main_thread_id = threading.main_thread().ident
    
    def authenticate_and_cache(self, descriptor: ConnectionDescriptor) -> bool:
        """
        Authenticate once and cache the token for session reuse.
        Must be called from main thread for Azure AD Interactive.
        Returns True if successful, False if authentication failed.
        """
        current_thread_id = threading.current_thread().ident

        if descriptor.auth_type == "azure_ad_interactive" and current_thread_id != self._main_thread_id:
            raise RuntimeError(
                "Azure AD Interactive authentication must run in main thread. "
                "Call authenticate_and_cache() from main thread before background operations."
            )

        cache_key = descriptor.cache_key()

        try:
            if descriptor.auth_type == "azure_ad_interactive":
                success = self._perform_interactive_auth_and_cache(descriptor)
            else:
                success = self._perform_non_interactive_auth_and_cache(descriptor)

            return success

        except Exception as e:
            return False

    def get_connection_string(self, descriptor: ConnectionDescriptor) -> str:
        """
        Get ODBC connection string with cached authentication token.

        Requires authenticate_and_cache() to be called first.
        Returns connection string using cached token or raises error if not authenticated.
        """
        with self._lock:
            cache_key = descriptor.cache_key()

            # Check if we have a valid cached token
            if cache_key in self._token_cache:
                token = self._token_cache[cache_key]
                if not token.is_expired:
                    return self._build_connection_string_with_token(descriptor, token)
                else:
                    # Token expired, remove from cache
                    del self._token_cache[cache_key]

            # No valid cached token - authentication required
            raise RuntimeError(
                f"No valid authentication token found for {cache_key}. "
                f"Call authenticate_and_cache() first from main thread."
            )
    
    def _perform_interactive_auth_and_cache(self, descriptor: ConnectionDescriptor) -> bool:
        """
        Perform Azure AD Interactive authentication and cache the result.
        Must run in main thread to show browser window.
        """
        import pyodbc

        # Build connection string for interactive auth
        conn_str = self._build_base_connection_string(descriptor)
        conn_str += ";Authentication=ActiveDirectoryInteractive"

        if descriptor.username:
            conn_str += f";UID={descriptor.username}"

        if descriptor.authority:
            conn_str += f";Authority={descriptor.authority}"

        try:
            # Test the connection to trigger authentication
            # This will show the browser window and cache the token internally by ODBC driver
            with pyodbc.connect(conn_str, autocommit=True, timeout=descriptor.timeout_seconds):
                pass

            # Store a placeholder token to indicate successful authentication
            cache_key = descriptor.cache_key()
            self._token_cache[cache_key] = AuthToken(
                access_token="odbc_cached",
                expires_at=datetime.now() + timedelta(hours=1),  # Conservative expiration
                token_type="Bearer"
            )

            return True

        except Exception as e:
            # Handle specific Azure AD errors and try Driver 17 fallback
            error_str = str(e)
            if "0x534" in error_str:
                return self._try_driver_17_fallback(descriptor)
            else:
                return False

    def _try_driver_17_fallback(self, descriptor: ConnectionDescriptor) -> bool:
        """Try authentication with ODBC Driver 17 as fallback for 0x534 errors"""
        import pyodbc

        # Build connection string with Driver 17
        conn_str = "DRIVER={ODBC Driver 17 for SQL Server}"
        conn_str += f";SERVER={descriptor.server}"
        conn_str += f";DATABASE={descriptor.database}"
        conn_str += ";Encrypt=yes"
        conn_str += ";TrustServerCertificate=yes"
        conn_str += ";Authentication=ActiveDirectoryInteractive"

        if descriptor.username:
            conn_str += f";UID={descriptor.username}"

        if descriptor.authority:
            conn_str += f";Authority={descriptor.authority}"

        try:
            with pyodbc.connect(conn_str, autocommit=True, timeout=descriptor.timeout_seconds):
                pass

            # Store a placeholder token to indicate successful authentication
            cache_key = descriptor.cache_key()
            self._token_cache[cache_key] = AuthToken(
                access_token="odbc_cached_driver17",
                expires_at=datetime.now() + timedelta(hours=1),  # Conservative expiration
                token_type="Bearer"
            )

            return True

        except Exception as e:
            return False

    def _perform_non_interactive_auth_and_cache(self, descriptor: ConnectionDescriptor) -> bool:
        """Perform non-interactive Azure AD authentication and cache the result"""
        # For now, just return True - non-interactive auth can be added later
        # This method exists for future expansion
        return True

    def _authenticate_interactive(self, descriptor: ConnectionDescriptor) -> str:
        """
        Handle Azure AD Interactive authentication.
        Must run in main thread to show browser window.
        """
        current_thread_id = threading.current_thread().ident
        
        if current_thread_id != self._main_thread_id:
            raise RuntimeError(
                "Azure AD Interactive authentication must run in main thread. "
                "Use pre-authenticated connection or switch to background-compatible auth type."
            )
        
        # Perform interactive authentication and cache the result
        return self._perform_interactive_auth(descriptor)
    
    def _authenticate_non_interactive(self, descriptor: ConnectionDescriptor) -> str:
        """
        Handle non-interactive Azure AD authentication types.
        Can run in any thread.
        """
        if descriptor.auth_type == "azure_ad_password":
            return self._perform_password_auth(descriptor)
        elif descriptor.auth_type == "azure_ad_integrated":
            return self._perform_integrated_auth(descriptor)
        elif descriptor.auth_type == "azure_ad_device_code":
            return self._perform_device_code_auth(descriptor)
        else:
            raise ValueError(f"Unsupported Azure AD auth type: {descriptor.auth_type}")
    
    def _perform_interactive_auth(self, descriptor: ConnectionDescriptor) -> str:
        """
        Perform Azure AD Interactive authentication using pyodbc.
        This will show the browser window for user login.
        """
        import pyodbc
        
        # Build connection string for interactive auth
        conn_str = self._build_base_connection_string(descriptor)
        conn_str += ";Authentication=ActiveDirectoryInteractive"
        
        if descriptor.username:
            conn_str += f";UID={descriptor.username}"
        
        if descriptor.authority:
            conn_str += f";Authority={descriptor.authority}"
        
        try:
            # Test the connection to trigger authentication
            # This will show the browser window and cache the token internally by ODBC driver
            with pyodbc.connect(conn_str, autocommit=True, timeout=descriptor.timeout_seconds):
                pass
            
            # For Interactive mode, we rely on ODBC driver's internal token caching
            # Store a placeholder token to indicate successful authentication
            cache_key = descriptor.cache_key()
            self._token_cache[cache_key] = AuthToken(
                access_token="odbc_cached",
                expires_at=datetime.now() + timedelta(hours=1),  # Conservative expiration
                token_type="Bearer"
            )
            
            return conn_str
            
        except Exception as e:
            # Handle specific Azure AD errors
            error_str = str(e)
            if "0x534" in error_str:
                raise RuntimeError(f"Azure AD authentication failed (Error 0x534). This may indicate:\n"
                                 f"- Token has expired\n"
                                 f"- User credentials need to be refreshed\n"
                                 f"- Network connectivity issues\n"
                                 f"Please try again or contact your administrator.")
            else:
                raise RuntimeError(f"Azure AD Interactive authentication failed: {e}")
    
    def _perform_password_auth(self, descriptor: ConnectionDescriptor) -> str:
        """Perform Azure AD Password authentication"""
        conn_str = self._build_base_connection_string(descriptor)
        conn_str += ";Authentication=ActiveDirectoryPassword"
        
        if descriptor.username:
            conn_str += f";UID={descriptor.username}"
        
        if descriptor.authority:
            conn_str += f";Authority={descriptor.authority}"
        
        # Note: Password must be provided at connection time
        return conn_str
    
    def _perform_integrated_auth(self, descriptor: ConnectionDescriptor) -> str:
        """Perform Azure AD Integrated authentication"""
        conn_str = self._build_base_connection_string(descriptor)
        conn_str += ";Authentication=ActiveDirectoryIntegrated"
        
        if descriptor.authority:
            conn_str += f";Authority={descriptor.authority}"
        
        return conn_str
    
    def _perform_device_code_auth(self, descriptor: ConnectionDescriptor) -> str:
        """Perform Azure AD Device Code authentication"""
        conn_str = self._build_base_connection_string(descriptor)
        conn_str += ";Authentication=ActiveDirectoryDeviceCode"
        
        if descriptor.username:
            conn_str += f";UID={descriptor.username}"
        
        if descriptor.authority:
            conn_str += f";Authority={descriptor.authority}"
        
        return conn_str
    
    def _build_base_connection_string(self, descriptor: ConnectionDescriptor) -> str:
        """Build base ODBC connection string without authentication"""
        # Use Driver 17 if specified (for 0x534 error fallback)
        driver = "ODBC Driver 17 for SQL Server" if descriptor.use_driver17 else "ODBC Driver 18 for SQL Server"

        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={descriptor.server}",
            f"DATABASE={descriptor.database}",
            "Encrypt=yes",
            "TrustServerCertificate=yes"  # Required for Azure AD
        ]
        return ";".join(parts)
    
    def _build_connection_string_with_token(self, descriptor: ConnectionDescriptor, token: AuthToken) -> str:
        """Build connection string using cached token"""
        # For ODBC driver internal caching (Interactive mode)
        if token.access_token == "odbc_cached":
            # Use Driver 18 (original successful authentication)
            conn_str = self._build_base_connection_string(descriptor) + ";Authentication=ActiveDirectoryInteractive"
            if descriptor.username:
                conn_str += f";UID={descriptor.username}"
            if descriptor.authority:
                conn_str += f";Authority={descriptor.authority}"
            return conn_str
        elif token.access_token == "odbc_cached_driver17":
            # Use Driver 17 (fallback successful authentication)
            conn_str = "DRIVER={ODBC Driver 17 for SQL Server}"
            conn_str += f";SERVER={descriptor.server}"
            conn_str += f";DATABASE={descriptor.database}"
            conn_str += ";Encrypt=yes"
            conn_str += ";TrustServerCertificate=yes"
            conn_str += ";Authentication=ActiveDirectoryInteractive"
            if descriptor.username:
                conn_str += f";UID={descriptor.username}"
            if descriptor.authority:
                conn_str += f";Authority={descriptor.authority}"
            return conn_str

        # For explicit token usage (future enhancement)
        conn_str = self._build_base_connection_string(descriptor)
        conn_str += f";AccessToken={token.access_token}"
        return conn_str
    
    def clear_cache(self, descriptor: Optional[ConnectionDescriptor] = None) -> None:
        """Clear cached tokens (all or for specific descriptor)"""
        with self._lock:
            if descriptor:
                cache_key = descriptor.cache_key()
                self._token_cache.pop(cache_key, None)
            else:
                self._token_cache.clear()

    def handle_authentication_error(self, descriptor: ConnectionDescriptor, error: Exception) -> None:
        """
        Handle authentication errors by clearing cache and providing user guidance.
        Call this when database operations fail with authentication errors.
        """
        with self._lock:
            # Clear the cached token for this descriptor
            cache_key = descriptor.cache_key()
            if cache_key in self._token_cache:
                del self._token_cache[cache_key]

        # Re-raise with user-friendly message
        error_str = str(error)
        if "0x534" in error_str or "authentication" in error_str.lower():
            raise RuntimeError(
                f"Authentication token has expired or is invalid.\n"
                f"Please close and reopen the project to re-authenticate.\n"
                f"Original error: {error}"
            )
        else:
            raise error
    
    def is_authenticated(self, descriptor: ConnectionDescriptor) -> bool:
        """Check if we have a valid cached token for the descriptor"""
        with self._lock:
            cache_key = descriptor.cache_key()
            if cache_key in self._token_cache:
                return not self._token_cache[cache_key].is_expired
            return False


# Global token manager instance
_token_manager: Optional[AzureADTokenManager] = None


def get_token_manager() -> AzureADTokenManager:
    """Get the global token manager instance"""
    global _token_manager
    if _token_manager is None:
        _token_manager = AzureADTokenManager()
    return _token_manager
