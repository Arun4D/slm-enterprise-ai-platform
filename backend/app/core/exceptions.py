"""
Exceptions and error taxonomy for the platform.

Implements structured error handling following enterprise patterns.
"""

from typing import Any


class PlatformException(Exception):
    """Base exception for all platform errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class PluginException(PlatformException):
    """Raised when plugin loading/execution fails."""

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message,
            error_code="PLUGIN_ERROR",
            status_code=400,
            details={**(details or {}), "plugin": plugin_name},
        )


class AgentException(PlatformException):
    """Raised when agent execution fails."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message,
            error_code="AGENT_ERROR",
            status_code=400,
            details={**(details or {}), "agent": agent_name},
        )


class SecurityException(PlatformException):
    """Raised when security constraints are violated."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            error_code="SECURITY_ERROR",
            status_code=403,
            details=details,
        )


class ValidationException(PlatformException):
    """Raised when validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class ResourceNotFoundException(PlatformException):
    """Raised when a requested resource is not found."""

    def __init__(
        self, resource_type: str, resource_id: str, details: dict[str, Any] | None = None
    ):
        super().__init__(
            f"{resource_type} not found: {resource_id}",
            error_code="NOT_FOUND",
            status_code=404,
            details={**(details or {}), "resource_type": resource_type, "resource_id": resource_id},
        )
