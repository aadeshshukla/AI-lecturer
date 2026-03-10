"""SQLite database connection and schema migration for the AI Lecturer.

Provides a single SQLAlchemy engine, session factory, and auto-creates
all tables on first run.

Tables created here:
  - students
  - lecture_sessions
  - classroom_events
  - tool_call_logs
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import DATABASE_URL

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


class StudentRecord(Base):
    """ORM mapping for the students table."""

    __tablename__ = "students"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    photo_path = Column(String, nullable=False, default="")
    email = Column(String, nullable=False, default="")
    attention_score = Column(Float, nullable=False, default=1.0)
    is_present = Column(Boolean, nullable=False, default=False)
    warning_count = Column(Integer, nullable=False, default=0)
    last_seen = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class LectureSessionRecord(Base):
    """ORM mapping for the lecture_sessions table."""

    __tablename__ = "lecture_sessions"

    id = Column(String, primary_key=True)
    topic = Column(String, nullable=False)
    difficulty = Column(String, nullable=False, default="intermediate")
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="starting")
    duration_minutes = Column(Integer, nullable=False, default=45)
    slides_generated = Column(Integer, nullable=False, default=0)
    tool_calls_made = Column(Integer, nullable=False, default=0)
    api_calls_used = Column(Integer, nullable=False, default=0)
    student_ids = Column(Text, nullable=False, default="")  # JSON list


class ClassroomEventRecord(Base):
    """ORM mapping for the classroom_events table."""

    __tablename__ = "classroom_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    data = Column(Text, nullable=False, default="{}")  # JSON
    handled = Column(Boolean, nullable=False, default=False)
    injected_to_gemini = Column(Boolean, nullable=False, default=False)


class ToolCallLogRecord(Base):
    """ORM mapping for the tool_call_logs table."""

    __tablename__ = "tool_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)
    args = Column(Text, nullable=False, default="{}")   # JSON
    result = Column(Text, nullable=False, default="{}")  # JSON
    called_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables if they do not already exist.

    Call this once at application startup before handling any requests.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified at %s", DATABASE_URL)


def get_db():
    """Yield a SQLAlchemy session and close it when done.

    Intended for use as a FastAPI dependency (``Depends(get_db)``).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
