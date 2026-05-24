"""
Conversational memory database and API models.
"""

import json
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.db import Base


# ===========================================================================
# SQLAlchemy Database Models
# ===========================================================================

class ConversationModel(Base):
    """SQLAlchemy model for chat sessions."""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    agent_id = Column(String(100), nullable=False, default="auto")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    # cascades ensure messages are deleted when a conversation is deleted
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")


class MessageModel(Base):
    """SQLAlchemy model for chat messages within a session."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system, or plan/execute indicators
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON-encoded dict for arbitrary agent metadata

    # Relationships
    conversation = relationship("ConversationModel", back_populates="messages")

    @property
    def msg_metadata(self) -> dict[str, Any]:
        """Convert database JSON-encoded metadata string back to dict."""
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {}

    @msg_metadata.setter
    def msg_metadata(self, val: dict[str, Any]) -> None:
        """Serialize dict to JSON string for database storage."""
        self.metadata_json = json.dumps(val) if val else None


# ===========================================================================
# Pydantic Schemas for API Serialization
# ===========================================================================

class MessageResponse(BaseModel):
    """Pydantic model representing a single chat message."""
    id: int
    session_id: str
    role: str
    text: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_custom(cls, obj: MessageModel) -> "MessageResponse":
        """Custom mapper to inject properties that require JSON decoding."""
        return cls(
            id=obj.id,
            session_id=obj.session_id,
            role=obj.role,
            text=obj.text,
            created_at=obj.created_at,
            metadata=obj.msg_metadata,
        )


class ConversationResponse(BaseModel):
    """Pydantic model representing a chat session."""
    id: str
    title: str
    agent_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Request schema for creating a new session."""
    title: Optional[str] = "New Chat"
    agent_id: Optional[str] = "auto"
