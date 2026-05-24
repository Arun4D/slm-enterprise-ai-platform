"""
Pydantic schemas for conversation and real-time streaming chat.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload representing a conversational prompt sent by the user."""
    session_id: Optional[str] = Field(
        default=None,
        description="Existing session UUID to continue, or null to start a new chat session."
    )
    message: str = Field(
        ...,
        description="The natural-language message or instruction."
    )
    agent_id: str = Field(
        default="auto",
        description="Target agent ID (e.g. 'log_analysis_agent', 'servicenow_agent') or 'auto' for SLM routing."
    )
    start_time: Optional[str] = Field(
        default=None,
        description="Optional start datetime boundary to filter logs during SRE operations (YYYY-MM-DD HH:MM:SS format)."
    )
    end_time: Optional[str] = Field(
        default=None,
        description="Optional end datetime boundary to filter logs during SRE operations (YYYY-MM-DD HH:MM:SS format)."
    )
