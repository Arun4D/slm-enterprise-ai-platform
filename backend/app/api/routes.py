"""
API routes for the platform.

Implements RESTful endpoints for agent execution, registry, health checks.
"""

import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import json
import asyncio
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings, ROOT_PATH
import sys
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from app.core.exceptions import PlatformException
from app.core.db import get_db
from app.services.memory_repository import MemoryRepository
from app.models.memory_models import ConversationResponse, MessageResponse, ConversationCreate
from app.models.chat_models import ChatRequest
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
    session_id: str | None = Form(None),
    start_time: str | None = Form(None),
    end_time: str | None = Form(None),
    file_path: str | None = Form(None),
    files: list[UploadFile] | None = File(None),
) -> dict:  # type: ignore
    """Upload browser-selected files or execute a local file/folder-oriented agent."""
    from app.main import agent_registry
    from app.security import path_validator

    if not agent_registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if agent_id != "log_analysis_agent":
        raise HTTPException(
            status_code=400,
            detail="File analysis is only enabled for log_analysis_agent",
        )

    # 1. Direct Local File Path Support (Runtime Configurable)
    if file_path:
        try:
            safe_path = path_validator.sanitize_path(file_path)
            if not safe_path.is_file():
                raise HTTPException(status_code=404, detail="Target log file not found.")

            # Proactively check read permission
            try:
                with safe_path.open("r", encoding="utf-8", errors="ignore") as f:
                    pass
            except PermissionError:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Permission Denied: The platform uvicorn server does not have read permissions "
                        f"for the local log file '{file_path}'. Please run 'chmod +r' on the file to "
                        "grant read access."
                    )
                )

            execution_intent = f"analyze log file: {intent}"
            result = await agent_registry.execute_agent(
                agent_id=agent_id,
                intent=execution_intent,
                context={
                    "intent": intent,
                    "log_file_path": str(safe_path),
                    "start_time": start_time,
                    "end_time": end_time,
                    "session_id": session_id or str(uuid4()),
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
            if isinstance(e, HTTPException):
                raise
            logger.error(f"Local file analysis error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # 2. Traditional Form Upload Support
    if not files:
        raise HTTPException(status_code=400, detail="At least one file or file path is required")

    folder_id = session_id or str(uuid4())
    upload_root = Path(settings.runtime_workspace_path) / "uploads" / folder_id
    upload_root.mkdir(parents=True, exist_ok=True)

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
                "start_time": start_time,
                "end_time": end_time,
                "session_id": folder_id,
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


@router.get("/agents/log_analysis_agent/tail")
async def tail_log_file(
    file_path: str,
    start_time: str | None = None,
    end_time: str | None = None,
):
    """
    Real-time SRE Log Tailing & Streaming diagnostics.
    Tails a local log file, parses new entries, updates statistics, and streams
    live updates to the client via SSE.
    """
    from app.security import path_validator
    try:
        safe_path = path_validator.sanitize_path(file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid file path: {str(e)}")

    if not safe_path.is_file():
        raise HTTPException(status_code=404, detail="Target log file not found.")

    # Proactively check read permission
    try:
        with safe_path.open("r", encoding="utf-8", errors="ignore") as f:
            pass
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=(
                "Permission Denied: The platform uvicorn server does not have read permissions "
                f"for the local log file '{file_path}'. Please run 'chmod +r' on the file to "
                "grant read access."
            )
        )

    async def log_tail_generator():
        from agents.log_analysis_agent.tools.log_parser import LogParser, LogAnalyzer
        import os

        # Aggregate metrics
        parsed_entries = []
        last_position = 0

        # Read initial contents (up to last 100 lines for SRE context)
        try:
            with safe_path.open("r", encoding="utf-8", errors="ignore") as f:
                file_size = os.path.getsize(safe_path)
                if file_size > 50 * 1024:  # > 50KB
                    f.seek(file_size - 50 * 1024)
                    f.readline()  # Skip first partial line
                
                content = f.read()
                last_position = f.tell()
                
                if content:
                    entries = LogParser.parse_text_log(content)
                    entries = LogParser.filter_entries_by_datetime(entries, start_time, end_time)
                    parsed_entries.extend(entries)

            classified = LogAnalyzer.classify_entries(parsed_entries)
            patterns = LogAnalyzer.extract_patterns(classified["errors"] + classified["warnings"])
            app_status = LogAnalyzer.detect_application_lifecycle(parsed_entries)

            yield f"data: {json.dumps({
                'event': 'init',
                'total_lines': len(parsed_entries),
                'classified': {
                    'info_count': len(classified['info']),
                    'error_count': len(classified['errors']),
                    'warning_count': len(classified['warnings']),
                },
                'patterns': patterns,
                'application_status': app_status,
                'raw_lines': [e['raw'] for e in parsed_entries[-40:]]
            })}\n\n"
            await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error initializing log tail generator: {e}")
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
            return

        try:
            while True:
                current_size = os.path.getsize(safe_path)
                if current_size < last_position:
                    last_position = 0  # Rollover/truncation support

                if current_size > last_position:
                    with safe_path.open("r", encoding="utf-8", errors="ignore") as f:
                        f.seek(last_position)
                        new_content = f.read()
                        last_position = f.tell()

                        if new_content:
                            new_entries = LogParser.parse_text_log(new_content)
                            new_entries = LogParser.filter_entries_by_datetime(new_entries, start_time, end_time)
                            
                            if new_entries:
                                parsed_entries.extend(new_entries)
                                classified = LogAnalyzer.classify_entries(parsed_entries)
                                patterns = LogAnalyzer.extract_patterns(classified["errors"] + classified["warnings"])
                                app_status = LogAnalyzer.detect_application_lifecycle(parsed_entries)

                                yield f"data: {json.dumps({
                                    'event': 'update',
                                    'total_lines': len(parsed_entries),
                                    'classified': {
                                        'info_count': len(classified['info']),
                                        'error_count': len(classified['errors']),
                                        'warning_count': len(classified['warnings']),
                                    },
                                    'patterns': patterns,
                                    'application_status': app_status,
                                    'raw_lines': [e['raw'] for e in new_entries]
                                })}\n\n"

                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("Log tail generator client disconnected.")
        except Exception as e:
            logger.error(f"Error in log tail generator: {e}")
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(log_tail_generator(), media_type="text/event-stream")


@router.get("/plugins")
async def list_plugins() -> dict:  # type: ignore
    """List all loaded plugins."""
    from app.main import plugin_manager

    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return {"plugins": plugin_manager.list_plugins()}


# ===========================================================================
# Conversational Memory & Real-Time SSE Chat Stream Routes
# ===========================================================================

@router.post("/sessions", response_model=ConversationResponse)
async def create_session(request: ConversationCreate, db: Session = Depends(get_db)):
    """Create a new conversational session."""
    repo = MemoryRepository(db)
    session = repo.create_session(title=request.title or "New Chat", agent_id=request.agent_id or "auto")
    return session


@router.get("/sessions", response_model=list[ConversationResponse])
async def list_sessions(db: Session = Depends(get_db)):
    """List all active and past chat sessions."""
    repo = MemoryRepository(db)
    return repo.list_sessions()


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    """Fetch all messages for a given session."""
    repo = MemoryRepository(db)
    messages = repo.get_session_messages(session_id)
    return [MessageResponse.from_orm_custom(m) for m in messages]


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a conversation session and all cascade records."""
    repo = MemoryRepository(db)
    success = repo.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": "Session deleted"}


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """
     Conversational Server-Sent Events (SSE) chat streaming endpoint.
     Performs dynamic SLM-based routing, compiles execution plans,
     runs background Python actions, and streams tokens to the client.
    """
    from app.main import agent_registry, slm_service

    if not agent_registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    repo = MemoryRepository(db)
    session_id = request.session_id or str(uuid4())

    # Ensure session exists or auto-create it
    session = repo.get_session(session_id)
    if not session:
        # Title is set to the beginning of user query
        title = request.message[:40] + "..." if len(request.message) > 40 else request.message
        session = repo.create_session(session_id=session_id, title=title, agent_id=request.agent_id)
    else:
        # Auto-update generic title to the user's first prompt
        if session.title == "New Chat":
            session.title = request.message[:40] + "..." if len(request.message) > 40 else request.message
            db.commit()

    # Log user prompt to persistent database memory
    repo.add_message(session_id=session_id, role="user", text=request.message)

    async def event_generator():
        try:
            target_agent_id = request.agent_id

            # 1. INTENT CLASSIFICATION & AGENT ROUTING
            if target_agent_id == "auto":
                yield f"data: {json.dumps({'event': 'routing', 'data': 'Classifying query intent using local SLM orchestrator...'})}\n\n"
                await asyncio.sleep(0.05)

                agent_labels = []
                for aid, ainfo in agent_registry.agents.items():
                    if not ainfo.get("enabled", True):
                        continue
                    metadata = ainfo["metadata"]
                    agent_labels.append((aid, metadata.description))

                if slm_service and slm_service.available:
                    classified_agent = await slm_service.classify_intent(request.message, agent_labels)
                    target_agent_id = classified_agent or "log_analysis_agent"
                else:
                    # Semantic Keyword-based Router Fallback (Ensures high accuracy in offline evaluation)
                    normalized_message = request.message.lower()
                    
                    snow_keywords = ["servicenow", "snow", "incident", "ticket", "inc", "rca", "resolution", "client", "close notes", "trends", "user", "db"]
                    log_keywords = ["log", "error", "tomcat", "java", "exception", "warn", "parse", "scan", "evtx", "diagnose"]
                    
                    snow_score = sum(1 for kw in snow_keywords if kw in normalized_message)
                    log_score = sum(1 for kw in log_keywords if kw in normalized_message)
                    
                    if "servicenow" in normalized_message or "snow" in normalized_message or "incident" in normalized_message or "ticket" in normalized_message or "inc" in normalized_message:
                        target_agent_id = "servicenow_agent"
                    elif log_score > snow_score:
                        target_agent_id = "log_analysis_agent"
                    elif snow_score > log_score:
                        target_agent_id = "servicenow_agent"
                    else:
                        target_agent_id = "log_analysis_agent"
                        
                    logger.info(f"SLM Service unavailable. Fallback router routed query to: {target_agent_id} (Scores - log: {log_score}, snow: {snow_score})")

            yield f"data: {json.dumps({'event': 'routing', 'data': f'Routed query to agent: {target_agent_id}'})}\n\n"
            await asyncio.sleep(0.05)

            # Retrieve concrete agent entry
            try:
                agent_entry = agent_registry.get_agent(target_agent_id)
                agent_instance = agent_entry["plugin"]["agent"]
            except Exception:
                target_agent_id = "log_analysis_agent"
                agent_entry = agent_registry.get_agent(target_agent_id)
                agent_instance = agent_entry["plugin"]["agent"]
                yield f"data: {json.dumps({'event': 'routing', 'data': f'Fallback routed to: {target_agent_id}'})}\n\n"

            agent_name = agent_entry["metadata"].name

            # 2. TASK DECOMPOSITION & PLANNING
            yield f"data: {json.dumps({'event': 'planning', 'data': f'Initializing agent planning layer for {agent_name}...'})}\n\n"
            await asyncio.sleep(0.05)

            session_messages = repo.get_session_messages(session_id)
            user_history = [m.text for m in session_messages if m.role == "user"]

            plan = await agent_instance.plan(
                request.message,
                {
                    "session_id": session_id,
                    "log_folder_path": str(Path(settings.runtime_workspace_path) / "uploads" / session_id),
                    "history": user_history,
                    "start_time": request.start_time,
                    "end_time": request.end_time,
                }
            )

            steps_list = plan.get("steps", [])
            steps_formatted = "\n".join(f"{idx+1}. {step}" for idx, step in enumerate(steps_list))
            planning_msg = f"Execution Plan Generated:\n{steps_formatted}"
            yield f"data: {json.dumps({'event': 'planning', 'data': planning_msg})}\n\n"
            await asyncio.sleep(0.1)

            # 3. DETERMINISTIC PYTHON EXECUTION
            yield f"data: {json.dumps({'event': 'execution', 'data': 'Executing Python agent workflows...'})}\n\n"
            await asyncio.sleep(0.05)

            result = await agent_instance.execute(plan)

            yield f"data: {json.dumps({'event': 'execution', 'data': 'Execution completed successfully. Synthesizing report...'})}\n\n"
            await asyncio.sleep(0.1)

            # 4. RESPONSE SUMMARIZATION & STREAMING
            summary = await agent_instance.summarize(result)

            # Split summary into words to simulate smooth token streaming chunks
            words = summary.split(" ")
            for idx, word in enumerate(words):
                chunk = word + (" " if idx < len(words) - 1 else "")
                yield f"data: {json.dumps({'event': 'token', 'data': chunk})}\n\n"
                await asyncio.sleep(0.012)  # Adaptive typewriter delay

            # Save the final structured agent response to DB memory
            repo.add_message(session_id=session_id, role="assistant", text=summary, metadata={"agent_id": target_agent_id})

            # Send final session details
            yield f"data: {json.dumps({'event': 'session', 'session_id': session_id, 'agent_id': target_agent_id})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as exc:
            logger.error(f"Error in SSE conversational stream: {exc}")
            yield f"data: {json.dumps({'event': 'error', 'data': f'Execution error: {str(exc)}'})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
