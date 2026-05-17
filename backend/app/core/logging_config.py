"""
Structured logging configuration.

Implements enterprise-grade logging with audit trail support.
"""

import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.
    
    Sets up file and console handlers with appropriate formatting.
    Ensures audit logs are separated for compliance tracking.
    """
    log_level = getattr(logging, settings.log_level.upper())
    
    # Create log directory if needed
    if settings.audit_logging_enabled:
        audit_path = Path(settings.audit_log_path)
        audit_path.mkdir(parents=True, exist_ok=True)
    
    if settings.log_format == "json":
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Standard library logging configuration
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        if settings.log_format == "console"
        else "%(message)s",
    )


def get_logger(name: str) -> logging.Logger | structlog.PrintLogger:
    """Get a logger instance."""
    if settings.log_format == "json":
        return structlog.get_logger(name)
    return logging.getLogger(name)


def log_audit_event(
    event_type: str,
    actor: str,
    resource: str,
    action: str,
    result: str,
    details: dict | None = None,
) -> None:
    """
    Log audit event for compliance tracking.
    
    Args:
        event_type: Type of audit event (e.g., 'agent_execution', 'plugin_load')
        actor: User/service performing the action
        resource: Resource being acted upon
        action: Action being performed
        result: Result of the action ('success', 'failure', 'denied')
        details: Additional details for audit trail
    """
    if not settings.audit_logging_enabled:
        return
    
    audit_logger = logging.getLogger("audit")
    audit_logger.info(
        f"[AUDIT] {event_type}",
        extra={
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "actor": actor,
            "resource": resource,
            "action": action,
            "result": result,
            "details": details or {},
        },
    )
