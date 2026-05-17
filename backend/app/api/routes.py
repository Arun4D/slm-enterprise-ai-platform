"""
API routes for the platform.

Implements RESTful endpoints for agent execution, registry, health checks.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.core.exceptions import PlatformException
from app.main import agent_registry
from app.models import AgentExecutionRequest, AgentExecutionResponse, HealthCheckResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["platform"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> dict:  # type: ignore
    """
    Health check endpoint.
    
    Returns platform status and agent health metrics.
    """
    if not agent_registry:
        return JSONResponse(
            status_code=503,
            content={"error": "Service not initialized"},
        )

    health_status = await agent_registry.health_check_all()
    healthy_count = sum(1 for v in health_status.values() if v)

    return {
        "status": "healthy" if healthy_count > 0 else "degraded",
        "version": "0.1.0",
        "uptime_seconds": 0.0,
        "agents_loaded": len(health_status),
        "agents_healthy": healthy_count,
    }


@router.get("/agents")
async def list_agents() -> dict:  # type: ignore
    """List all registered agents."""
    if not agent_registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return {"agents": agent_registry.list_agents()}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict:  # type: ignore
    """Get agent details by ID."""
    if not agent_registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        agent = agent_registry.get_agent(agent_id)
        return {
            "id": agent_id,
            "name": agent["metadata"].name,
            "version": agent["metadata"].version,
            "description": agent["metadata"].description,
            "capabilities": agent["metadata"].capabilities,
            "status": agent["status"].value,
            "enabled": agent["enabled"],
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/agents/{agent_id}/execute", response_model=AgentExecutionResponse)
async def execute_agent(agent_id: str, request: AgentExecutionRequest) -> dict:  # type: ignore
    """Execute an agent."""
    if not agent_registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        result = await agent_registry.execute_agent(
            agent_id=agent_id,
            intent=request.input_data.get("intent", ""),
            context=request.input_data,
        )

        return {
            "execution_id": f"exec_{agent_id}_{datetime.utcnow().timestamp()}",
            "agent_id": agent_id,
            "status": result["status"],
            "result": result.get("result"),
            "execution_time_ms": 0.0,
        }

    except PlatformException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Execution error: {e}")
        raise HTTPException(status_code=500, detail="Execution failed")


@router.get("/plugins")
async def list_plugins() -> dict:  # type: ignore
    """List all loaded plugins."""
    from app.main import plugin_manager

    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return {"plugins": plugin_manager.list_plugins()}
