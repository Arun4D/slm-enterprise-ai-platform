"""
Application configuration management.

Implements config-driven architecture with environment-based overrides.
Follows 12-factor app principles for enterprise deployments.
"""

import logging
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with validation.
    
    Environment variables override defaults.
    """

    # FastAPI
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    app_name: str = "SLM Enterprise AI Platform"
    app_version: str = "0.1.0"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # SLM Model Configuration
    slm_model_path: str = "/models/phi-3-mini-gguf/model.gguf"
    slm_model_context_size: int = 2048
    slm_model_threads: int = 4
    slm_model_gpu_layers: int = 0  # Set > 0 to offload to GPU

    # Security
    jwt_secret_key: str = "change-this-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Plugin System
    plugin_auto_discovery: bool = True
    plugin_allowed_paths: list[str] = ["/agents", "/plugins"]
    plugin_trusted_sources: str = "internal"

    # Audit
    audit_logging_enabled: bool = True
    audit_log_path: str = "/logs/audit"

    # Agent Constraints
    agent_execution_timeout_seconds: int = 300
    agent_memory_limit_mb: int = 512

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Configure logging based on settings
if settings.log_format == "json":
    import structlog
    
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
    logger = structlog.get_logger()
else:
    logging.basicConfig(level=settings.log_level)
    logger = logging.getLogger(__name__)
