"""
API routes for the platform.

Implements RESTful endpoints for agent execution, registry, health checks.
"""

import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import PlatformException
from app.models import AgentExecutionRequest, AgentExecutionResponse, HealthCheckResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["platform"])


def _safe_upload_path(upload_root: Path, filename: str | None) -> Path:
    """Build a path under upload_root while preserving safe relative folders."""
    raw_name = (filename or "uploaded.log").replace("\\", "/").replace("\x00", "")
    parts = [
        part.strip()
        for part in raw_name.split("/")
        if part.strip() and part.strip() not in {".", ".."}
    ]
    safe_parts = parts or ["uploaded.log"]
    return upload_root.joinpath(*safe_parts)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> dict:  # type: ignore
    """
    Health check endpoint.
    
    Returns platform status and agent health metrics.
    """
    from app.main import agent_registry

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
    from app.main import agent_registry

    if not agent_registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return {"agents": agent_registry.list_agents()}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict:  # type: ignore
    """Get agent details by ID."""
    from app.main import agent_registry

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
    from app.main import agent_registry

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
            "result": {
                **(result.get("result") or {}),
                "summary": result.get("summary", ""),
            },
            "execution_time_ms": 0.0,
        }

    except PlatformException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Execution error: {e}")
        raise HTTPException(status_code=500, detail="Execution failed")


@router.post("/agents/{agent_id}/analyze-files", response_model=AgentExecutionResponse)
async def analyze_agent_files(
    agent_id: str,
    intent: str = Form("analyze log files uploaded from frontend"),
    files: list[UploadFile] = File(...),
) -> dict:  # type: ignore
    """Upload browser-selected files and execute a file/folder-oriented agent."""
    from app.main import agent_registry

    if not agent_registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if agent_id != "log_analysis_agent":
        raise HTTPException(
            status_code=400,
            detail="File analysis is only enabled for log_analysis_agent",
        )

    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    upload_root = Path(settings.runtime_workspace_path) / "uploads" / str(uuid4())
    upload_root.mkdir(parents=True, exist_ok=False)

    try:
        for upload in files:
            destination = _safe_upload_path(upload_root, upload.filename)
            destination.parent.mkdir(parents=True, exist_ok=True)

            with destination.open("wb") as out_file:
                while chunk := await upload.read(1024 * 1024):
                    out_file.write(chunk)

        execution_intent = f"analyze log files: {intent}"
        result = await agent_registry.execute_agent(
            agent_id=agent_id,
            intent=execution_intent,
            context={
                "intent": intent,
                "log_folder_path": str(upload_root),
            },
        )

        return {
            "execution_id": f"exec_{agent_id}_{datetime.utcnow().timestamp()}",
            "agent_id": agent_id,
            "status": result["status"],
            "result": {
                **(result.get("result") or {}),
                "summary": result.get("summary", ""),
            },
            "execution_time_ms": 0.0,
        }

    except PlatformException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"File analysis error: {e}")
        raise HTTPException(status_code=500, detail="File analysis failed")


@router.get("/plugins")
async def list_plugins() -> dict:  # type: ignore
    """List all loaded plugins."""
    from app.main import plugin_manager

    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return {"plugins": plugin_manager.list_plugins()}
