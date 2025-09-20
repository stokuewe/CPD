"""
Secure credential manager for database passwords.

Provides secure in-memory storage of database credentials during application runtime.
Uses OS-level encryption and follows security best practices.
"""

import os
import sys
from typing import Optional, Dict
import threading
from dataclasses import dataclass


@dataclass
class DatabaseCredentials:
    """Secure container for database credentials"""
    server: str
    database: str
    username: str
    auth_type: str
    _encrypted_password: Optional[bytes] = None
    
    def __post_init__(self):
        # Ensure password is never stored as plain text in this object
        pass


class SecureCredentialManager:
    """
    Secure credential manager for database passwords.
    
    Features:
    - OS-level encryption using Windows DPAPI / macOS Keychain / Linux Secret Service
    - In-memory encryption for active sessions
    - Automatic cleanup on application exit
    - Thread-safe access
    - No plain text storage
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._session_credentials: Dict[str, bytes] = {}  # project_path -> encrypted_password
        self._encryption_key: Optional[bytes] = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption system based on OS"""
        try:
            if sys.platform == "win32":
                self._init_windows_encryption()
            elif sys.platform == "darwin":
                self._init_macos_encryption()
            else:
                self._init_linux_encryption()
        except Exception:
            # Fallback to basic in-memory encryption
            self._init_fallback_encryption()
    
    def _init_windows_encryption(self):
        """Initialize Windows DPAPI encryption"""
        try:
            import win32crypt
            self._encrypt_func = self._encrypt_windows
            self._decrypt_func = self._decrypt_windows
        except ImportError:
            self._init_fallback_encryption()
    
    def _init_macos_encryption(self):
        """Initialize macOS Keychain encryption"""
        try:
            # Use python-keyring for macOS
            import keyring
            self._encrypt_func = self._encrypt_keyring
            self._decrypt_func = self._decrypt_keyring
        except ImportError:
            self._init_fallback_encryption()
    
    def _init_linux_encryption(self):
        """Initialize Linux Secret Service encryption"""
        try:
            # Use python-keyring for Linux
            import keyring
            self._encrypt_func = self._encrypt_keyring
            self._decrypt_func = self._decrypt_keyring
        except ImportError:
            self._init_fallback_encryption()
    
    def _init_fallback_encryption(self):
        """Fallback encryption using cryptography library"""
        try:
            from cryptography.fernet import Fernet
            self._encryption_key = Fernet.generate_key()
            self._fernet = Fernet(self._encryption_key)
            self._encrypt_func = self._encrypt_fallback
            self._decrypt_func = self._decrypt_fallback
        except ImportError:
            # Last resort: XOR obfuscation (not secure, but better than plain text)
            self._encryption_key = os.urandom(32)
            self._encrypt_func = self._encrypt_xor
            self._decrypt_func = self._decrypt_xor
    
    def _encrypt_windows(self, data: str) -> bytes:
        """Encrypt using Windows DPAPI"""
        import win32crypt
        return win32crypt.CryptProtectData(data.encode('utf-8'), None, None, None, None, 0)
    
    def _decrypt_windows(self, encrypted_data: bytes) -> str:
        """Decrypt using Windows DPAPI"""
        import win32crypt
        return win32crypt.CryptUnprotectData(encrypted_data, None, None, None, 0)[1].decode('utf-8')
    
    def _encrypt_keyring(self, data: str) -> bytes:
        """Encrypt using system keyring (macOS/Linux)"""
        import keyring
        # For session storage, we'll use a combination approach
        # Store in keyring with session-specific key
        session_key = f"cpd_session_{os.getpid()}"
        keyring.set_password("CPD_Database", session_key, data)
        return session_key.encode('utf-8')
    
    def _decrypt_keyring(self, encrypted_data: bytes) -> str:
        """Decrypt using system keyring (macOS/Linux)"""
        import keyring
        session_key = encrypted_data.decode('utf-8')
        password = keyring.get_password("CPD_Database", session_key)
        if password is None:
            raise ValueError("Password not found in keyring")
        return password
    
    def _encrypt_fallback(self, data: str) -> bytes:
        """Encrypt using cryptography library"""
        return self._fernet.encrypt(data.encode('utf-8'))
    
    def _decrypt_fallback(self, encrypted_data: bytes) -> str:
        """Decrypt using cryptography library"""
        return self._fernet.decrypt(encrypted_data).decode('utf-8')
    
    def _encrypt_xor(self, data: str) -> bytes:
        """XOR obfuscation (fallback only)"""
        data_bytes = data.encode('utf-8')
        key_bytes = self._encryption_key
        result = bytearray()
        for i, byte in enumerate(data_bytes):
            result.append(byte ^ key_bytes[i % len(key_bytes)])
        return bytes(result)
    
    def _decrypt_xor(self, encrypted_data: bytes) -> str:
        """XOR deobfuscation (fallback only)"""
        key_bytes = self._encryption_key
        result = bytearray()
        for i, byte in enumerate(encrypted_data):
            result.append(byte ^ key_bytes[i % len(key_bytes)])
        return result.decode('utf-8')
    
    def store_password(self, project_path: str, password: str) -> None:
        """
        Store password securely for the current session.

        Args:
            project_path: Unique identifier for the project
            password: Database password to store securely
        """
        with self._lock:
            if not password:
                return

            try:
                encrypted_password = self._encrypt_func(password)
                self._session_credentials[project_path] = encrypted_password

                # Clear the original password from memory
                # Note: This doesn't guarantee memory is cleared, but it's a best effort
                password = "0" * len(password)
                del password

            except Exception as e:
                raise RuntimeError(f"Failed to store password securely: {e}")
    
    def get_password(self, project_path: str) -> Optional[str]:
        """
        Retrieve password securely for the current session.
        
        Args:
            project_path: Unique identifier for the project
            
        Returns:
            Decrypted password or None if not found
        """
        with self._lock:
            encrypted_password = self._session_credentials.get(project_path)
            if encrypted_password is None:
                return None

            try:
                return self._decrypt_func(encrypted_password)
            except Exception as e:
                # If decryption fails, remove the corrupted entry
                self._session_credentials.pop(project_path, None)
                raise RuntimeError(f"Failed to retrieve password securely: {e}")
    
    def clear_password(self, project_path: str) -> None:
        """
        Clear password for a specific project.
        
        Args:
            project_path: Unique identifier for the project
        """
        with self._lock:
            self._session_credentials.pop(project_path, None)
    
    def clear_all_passwords(self) -> None:
        """Clear all stored passwords (call on application exit)"""
        with self._lock:
            # Clear keyring entries if using keyring
            if hasattr(self, '_decrypt_keyring'):
                try:
                    import keyring
                    for encrypted_data in self._session_credentials.values():
                        try:
                            session_key = encrypted_data.decode('utf-8')
                            keyring.delete_password("CPD_Database", session_key)
                        except Exception:
                            pass  # Ignore cleanup errors
                except ImportError:
                    pass
            
            self._session_credentials.clear()
    
    def has_password(self, project_path: str) -> bool:
        """
        Check if password is stored for a project.
        
        Args:
            project_path: Unique identifier for the project
            
        Returns:
            True if password is stored, False otherwise
        """
        with self._lock:
            return project_path in self._session_credentials


# Global instance
_credential_manager: Optional[SecureCredentialManager] = None


def get_credential_manager() -> SecureCredentialManager:
    """Get the global credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = SecureCredentialManager()
    return _credential_manager


def cleanup_credentials():
    """Cleanup function to call on application exit"""
    global _credential_manager
    if _credential_manager is not None:
        _credential_manager.clear_all_passwords()
        _credential_manager = None
