"""
Application configuration management.

Implements config-driven architecture with environment-based overrides.
Follows 12-factor app principles for enterprise deployments.
"""

import logging
import json
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_PATH = Path(__file__).resolve().parents[3]


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
    cors_origins: list[str] | str = [
        "http://localhost:3000",
        "http://localhost:8001",
        "http://localhost:4173",
    ]

    # SLM Model Configuration
    slm_enabled: bool = True  # Master toggle for SLM features
    slm_model_path: str = str(ROOT_PATH / "backend" / "models" / "qwen2.5-coder-1.5b-instruct-gguf" / "model.gguf")
    slm_model_context_size: int = 2048
    slm_model_threads: int = 4
    slm_model_gpu_layers: int = 0  # Set > 0 to offload to GPU

    # Relational Conversational Memory
    sqlite_db_url: str = f"sqlite:///{ROOT_PATH}/backend/app.db"

    # SLM Inference Tuning
    slm_temperature: float = 0.1  # 0.0 = deterministic, higher = more creative
    slm_max_tokens: int = 256  # Default max tokens per generation
    slm_top_p: float = 0.9  # Nucleus sampling threshold

    # Security
    jwt_secret_key: str = "change-this-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Plugin System
    plugin_auto_discovery: bool = True
    plugin_allowed_paths: list[str] | str = [
        str(ROOT_PATH / "agents"),
        str(ROOT_PATH / "plugins"),
    ]
    plugin_trusted_sources: str = "internal"
    runtime_workspace_path: str = str(Path(tempfile.gettempdir()) / "slm-enterprise-ai-platform")
    extra_allowed_paths: list[str] | str = []
    file_allowed_paths: list[str] | str = [
        str(ROOT_PATH / "agents"),
        str(ROOT_PATH / "plugins"),
        str(Path(tempfile.gettempdir()) / "slm-enterprise-ai-platform"),
        str(Path.home() / "Workspace"),
        str(ROOT_PATH),
    ]

    # Audit
    audit_logging_enabled: bool = True
    audit_log_path: str = "logs/audit"

    # Agent Constraints
    agent_execution_timeout_seconds: int = 300
    agent_memory_limit_mb: int = 512

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: object) -> object:
        """Accept common environment labels that appear in DEBUG variables."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "off"}:
                return False
            if normalized in {"dev", "development", "on"}:
                return True
        return value

    @field_validator("extra_allowed_paths", "file_allowed_paths", "plugin_allowed_paths", "cors_origins", mode="before")
    @classmethod
    def parse_list_setting(cls, value: object) -> object:
        """Accept JSON arrays or comma-separated strings in .env files."""
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.startswith("["):
                return json.loads(normalized)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def resolved_file_allowed_paths(self) -> list[str]:
        """Base allowlist plus operator-provided extra paths."""
        return [*self._as_list(self.file_allowed_paths), *self._as_list(self.extra_allowed_paths)]

    @staticmethod
    def _as_list(value: list[str] | str) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


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
