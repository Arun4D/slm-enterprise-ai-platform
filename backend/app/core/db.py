"""
Database engine and session management.
Provides thread-safe access to SQLite database.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create SQLite engine
# 'check_same_thread=False' allows SQLite to be used in async FastAPI contexts safely across threads
engine = create_engine(
    settings.sqlite_db_url,
    connect_args={"check_same_thread": False} if settings.sqlite_db_url.startswith("sqlite") else {}
)

# Create scoped session factory
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(session_factory)

# Declarative base class for models
Base = declarative_base()


def get_db():  # type: ignore
    """
    FastAPI dependency injection provider for DB sessions.
    Ensures the session is closed after the request lifecycle.
    """
    db = db_session()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    try:
        logger.info("Initializing SQLite database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as exc:
        logger.error(f"Error initializing database: {exc}")
        raise
