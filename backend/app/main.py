"""
FastAPI application factory and main entry point.

Implements dependency injection and application lifecycle management.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.slm.engine import SLMEngine
from app.core.slm.service import SLMService
from app.services.agent_registry import AgentRegistry
from app.services.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


# Global instances
plugin_manager: PluginManager | None = None
agent_registry: AgentRegistry | None = None
slm_service: SLMService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events.
    """
    global plugin_manager, agent_registry, slm_service

    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    setup_logging()
    
    # Initialize SQLite database
    from app.core.db import init_db
    init_db()
    
    # Initialize SLM engine and service
    slm_engine = SLMEngine(
        model_path=settings.slm_model_path,
        context_size=settings.slm_model_context_size,
        threads=settings.slm_model_threads,
        gpu_layers=settings.slm_model_gpu_layers,
    )
    slm_service = SLMService(slm_engine)
    if slm_service.available:
        logger.info("SLM service initialized")
    else:
        logger.warning(
            "SLM service unavailable — agents will use deterministic fallbacks. "
            f"Reason: {slm_engine.load_error or 'model not found'}. "
            f"Path: {settings.slm_model_path}"
        )
    
    # Initialize services
    plugin_manager = PluginManager()
    agent_registry = AgentRegistry(plugin_manager)
    
    # Discover and load agents
    try:
        await agent_registry.initialize()
        # Inject SLM service into each agent that accepts it
        for agent_id, entry in agent_registry.agents.items():
            agent_instance = entry["plugin"]["agent"]
            if hasattr(agent_instance, 'set_slm_service'):
                agent_instance.set_slm_service(slm_service)
                logger.info(f"Injected SLM service into agent: {agent_id}")
        health_status = await agent_registry.health_check_all()
        healthy_count = sum(1 for v in health_status.values() if v)
        logger.info(f"Agent health check: {healthy_count}/{len(health_status)} healthy")
    except Exception as e:
        logger.error(f"Error initializing agents: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    slm_engine.shutdown()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Enterprise AI Operations Platform with Small Language Models",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(routes.router)

    return app


# Create app instance
app = create_app()


@app.exception_handler(Exception)  # type: ignore
async def general_exception_handler(request, exc):  # type: ignore
    """Handle uncaught exceptions."""
    from app.core.exceptions import PlatformException
    from fastapi import Request
    from fastapi.responses import JSONResponse

    logger.error(f"Unhandled exception: {exc}")

    if isinstance(exc, PlatformException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
        },
    )
