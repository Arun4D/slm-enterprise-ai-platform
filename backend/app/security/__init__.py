"""
Security module providing RBAC, input validation, and path allowlisting.

Implements zero-trust security model with defense-in-depth.
"""

import logging
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.exceptions import SecurityException

logger = logging.getLogger(__name__)


class PathValidator:
    """
    Validates and sanitizes file paths.
    
    Implements path allowlisting to prevent directory traversal attacks.
    """

    def __init__(self, allowed_paths: list[str] | None = None):
        """
        Initialize path validator.
        
        Args:
            allowed_paths: List of allowed directory paths
        """
        self.allowed_paths = [Path(p).resolve() for p in (allowed_paths or settings.file_allowed_paths)]

    def is_safe_path(self, path: str) -> bool:
        """
        Check if a path is within allowed directories.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path is safe, False otherwise
            
        Raises:
            SecurityException: If path traversal attack is detected
        """
        try:
            resolved_path = Path(path).resolve()
            
            # Check for null bytes
            if '\0' in str(path):
                raise SecurityException(f"Null byte detected in path: {path}")
            
            # Verify path is within allowed directories
            for allowed_path in self.allowed_paths:
                try:
                    resolved_path.relative_to(allowed_path)
                    logger.debug(f"Path validation passed: {path}")
                    return True
                except ValueError:
                    continue
            
            logger.warning(f"Path outside allowed directories: {path}")
            raise SecurityException(
                f"Path access denied: {path}",
                details={"path": str(path), "allowed_paths": [str(p) for p in self.allowed_paths]},
            )
        except Exception as e:
            if isinstance(e, SecurityException):
                raise
            logger.error(f"Path validation error: {e}")
            raise SecurityException(f"Invalid path: {path}")

    def sanitize_path(self, path: str) -> Path:
        """
        Sanitize and validate a path.
        
        Args:
            path: Path to sanitize
            
        Returns:
            Resolved Path object if valid
            
        Raises:
            SecurityException: If path is unsafe
        """
        if not self.is_safe_path(path):
            raise SecurityException(f"Path denied: {path}")
        return Path(path).resolve()


class InputValidator:
    """
    Validates and sanitizes user input.
    
    Prevents common injection attacks.
    """

    MAX_STRING_LENGTH = 10000
    MAX_ARRAY_LENGTH = 1000
    DANGEROUS_PATTERNS = [
        "__import__",
        "eval",
        "exec",
        "compile",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
    ]

    @classmethod
    def validate_agent_input(cls, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate agent input data.
        
        Args:
            input_data: Input to validate
            
        Returns:
            Validated input data
            
        Raises:
            SecurityException: If input contains dangerous content
        """
        if not isinstance(input_data, dict):
            raise SecurityException("Agent input must be a dictionary")
        
        for key, value in input_data.items():
            cls._validate_value(key, value)
        
        return input_data

    @classmethod
    def _validate_value(cls, key: str, value: Any) -> None:
        """
        Validate a single value recursively.
        
        Args:
            key: Field name
            value: Value to validate
            
        Raises:
            SecurityException: If value is dangerous
        """
        if isinstance(value, str):
            if len(value) > cls.MAX_STRING_LENGTH:
                raise SecurityException(f"String too long: {key}")
            if any(pattern in value for pattern in cls.DANGEROUS_PATTERNS):
                raise SecurityException(f"Dangerous pattern detected in {key}")
        elif isinstance(value, list):
            if len(value) > cls.MAX_ARRAY_LENGTH:
                raise SecurityException(f"Array too long: {key}")
            for item in value:
                cls._validate_value(f"{key}[]", item)
        elif isinstance(value, dict):
            for nested_key, nested_value in value.items():
                cls._validate_value(f"{key}.{nested_key}", nested_value)


class RBACManager:
    """
    Role-Based Access Control manager.
    
    Ready for integration with enterprise identity systems.
    """

    def __init__(self):
        """Initialize RBAC manager."""
        self.roles = {
            "admin": ["agent:execute", "agent:create", "plugin:load", "plugin:unload"],
            "operator": ["agent:execute", "plugin:view"],
            "viewer": ["agent:view", "plugin:view"],
        }

    def has_permission(self, role: str, permission: str) -> bool:
        """
        Check if role has permission.
        
        Args:
            role: User role
            permission: Required permission
            
        Returns:
            True if role has permission
        """
        return permission in self.roles.get(role, [])

    def check_permission(self, role: str, permission: str) -> None:
        """
        Verify permission or raise exception.
        
        Args:
            role: User role
            permission: Required permission
            
        Raises:
            SecurityException: If permission denied
        """
        if not self.has_permission(role, permission):
            raise SecurityException(
                f"Permission denied: {permission}",
                details={"role": role, "permission": permission},
            )


# Global security instances
path_validator = PathValidator()
rbac_manager = RBACManager()
