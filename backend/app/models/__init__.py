"""
Data models for API contracts.

Uses Pydantic for validation and serialization.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    LOADING = "loading"


class AgentMetadata(BaseModel):
    """Agent manifest metadata."""

    name: str = Field(..., description="Unique agent identifier")
    version: str = Field(..., description="Agent version")
    description: str = Field(..., description="Agent description")
    author: str = Field(..., description="Agent author")
    tags: list[str] = Field(default_factory=list, description="Agent tags for discovery")
    min_llm_version: str | None = Field(None, description="Minimum LLM version required")
    capabilities: list[str] = Field(
        default_factory=list, description="List of capabilities provided by agent"
    )
    requires_approval: bool = Field(
        default=False, description="Requires human approval before execution"
    )
    permission_scope: list[str] = Field(
        default_factory=list, description="Required permission scopes"
    )


class AgentRegistry(BaseModel):
    """Registry entry for an agent."""

    id: str = Field(..., description="Unique agent ID")
    metadata: AgentMetadata
    status: AgentStatus = AgentStatus.LOADING
    enabled: bool = True
    last_health_check: datetime | None = None
    error_message: str | None = None


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: 'user', 'assistant', 'system'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(BaseModel):
    """Chat session model."""

    session_id: str
    messages: list[ChatMessage] = []
    agent_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentExecutionRequest(BaseModel):
    """Request to execute an agent."""

    agent_id: str = Field(..., description="Agent to execute")
    input_data: dict = Field(default_factory=dict, description="Agent input")
    session_id: str | None = Field(None, description="Session context")
    require_approval: bool = False


class AgentExecutionResponse(BaseModel):
    """Response from agent execution."""

    execution_id: str
    agent_id: str
    status: str  # 'success', 'failure', 'pending_approval'
    result: dict | None = None
    error: str | None = None
    execution_time_ms: float = 0.0


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    uptime_seconds: float
    agents_loaded: int
    agents_healthy: int
