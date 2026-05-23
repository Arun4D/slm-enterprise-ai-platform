"""
Conversational memory repository implementation.
Handles database CRUD actions for sessions and chat history.
"""

import logging
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models.memory_models import ConversationModel, MessageModel

logger = logging.getLogger(__name__)


class MemoryRepository:
    """
    Relational repository for persistent conversational memory.
    """

    def __init__(self, db: Session):
        self._db = db

    def create_session(
        self,
        title: str = "New Chat",
        agent_id: str = "auto",
        session_id: str | None = None,
    ) -> ConversationModel:
        """Create a new conversational session."""
        sid = session_id or str(uuid4())
        session = ConversationModel(
            id=sid,
            title=title,
            agent_id=agent_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        try:
            self._db.add(session)
            self._db.commit()
            self._db.refresh(session)
            logger.info(f"Created conversation session: {sid}")
            return session
        except Exception as exc:
            self._db.rollback()
            logger.error(f"Error creating conversation session: {exc}")
            raise

    def get_session(self, session_id: str) -> ConversationModel | None:
        """Fetch a session by ID."""
        return self._db.query(ConversationModel).filter(ConversationModel.id == session_id).first()

    def list_sessions(self) -> list[ConversationModel]:
        """Fetch all sessions ordered by updated_at descending."""
        return self._db.query(ConversationModel).order_by(ConversationModel.updated_at.desc()).all()

    def delete_session(self, session_id: str) -> bool:
        """Delete a conversational session and all its messages."""
        session = self.get_session(session_id)
        if not session:
            return False
        try:
            self._db.delete(session)
            self._db.commit()
            logger.info(f"Deleted conversation session: {session_id}")
            return True
        except Exception as exc:
            self._db.rollback()
            logger.error(f"Error deleting session {session_id}: {exc}")
            raise

    def add_message(
        self,
        session_id: str,
        role: str,
        text: str,
        metadata: dict | None = None,
    ) -> MessageModel:
        """
        Add a message to a session and update the session's updated_at timestamp.
        """
        session = self.get_session(session_id)
        if not session:
            # Auto-create the session if it doesn't exist to prevent failure
            session = self.create_session(session_id=session_id)

        msg = MessageModel(
            session_id=session_id,
            role=role,
            text=text,
            created_at=datetime.utcnow(),
        )
        if metadata:
            msg.msg_metadata = metadata

        try:
            self._db.add(msg)
            # Update parent session's updated_at timestamp
            session.updated_at = datetime.utcnow()
            self._db.commit()
            self._db.refresh(msg)
            return msg
        except Exception as exc:
            self._db.rollback()
            logger.error(f"Error adding message to session {session_id}: {exc}")
            raise

    def get_session_messages(self, session_id: str) -> list[MessageModel]:
        """Retrieve all messages in a session ordered by created_at ascending."""
        return (
            self._db.query(MessageModel)
            .filter(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.asc())
            .all()
        )
