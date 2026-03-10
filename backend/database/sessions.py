"""Lecture session logging and tool-call tracking for the AI Lecturer database."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.database.db import LectureSessionRecord, ToolCallLogRecord
from backend.models.lecture import LectureSession

logger = logging.getLogger(__name__)


def _to_model(record: LectureSessionRecord) -> LectureSession:
    """Convert a LectureSessionRecord ORM object to a LectureSession dataclass."""
    student_ids: list[str] = []
    if record.student_ids:
        try:
            student_ids = json.loads(record.student_ids)
        except json.JSONDecodeError:
            student_ids = []
    return LectureSession(
        id=record.id,
        topic=record.topic,
        difficulty=record.difficulty,
        started_at=record.started_at,
        ended_at=record.ended_at,
        status=record.status,
        duration_minutes=record.duration_minutes,
        slides_generated=record.slides_generated,
        tool_calls_made=record.tool_calls_made,
        api_calls_used=record.api_calls_used,
        student_ids=student_ids,
    )


def create_session(db: Session, session: LectureSession) -> LectureSession:
    """Persist a new LectureSession and return it.

    Args:
        db: Active SQLAlchemy session.
        session: LectureSession dataclass to persist.

    Returns:
        The persisted LectureSession.
    """
    record = LectureSessionRecord(
        id=session.id,
        topic=session.topic,
        difficulty=session.difficulty,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        duration_minutes=session.duration_minutes,
        slides_generated=session.slides_generated,
        tool_calls_made=session.tool_calls_made,
        api_calls_used=session.api_calls_used,
        student_ids=json.dumps(session.student_ids),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info("Created lecture session %s — topic: %s", session.id, session.topic)
    return _to_model(record)


def get_session(db: Session, session_id: str) -> Optional[LectureSession]:
    """Fetch a lecture session by ID, or None if not found."""
    record = (
        db.query(LectureSessionRecord)
        .filter(LectureSessionRecord.id == session_id)
        .first()
    )
    return _to_model(record) if record else None


def update_session_status(db: Session, session_id: str, status: str) -> None:
    """Update the lifecycle status of a lecture session."""
    record = (
        db.query(LectureSessionRecord)
        .filter(LectureSessionRecord.id == session_id)
        .first()
    )
    if not record:
        logger.warning("update_session_status: session %s not found", session_id)
        return
    record.status = status
    db.commit()
    logger.info("Session %s status → %s", session_id, status)


def end_session(db: Session, session_id: str) -> None:
    """Mark a session as ended and record the end timestamp."""
    record = (
        db.query(LectureSessionRecord)
        .filter(LectureSessionRecord.id == session_id)
        .first()
    )
    if not record:
        logger.warning("end_session: session %s not found", session_id)
        return
    record.status = "ended"
    record.ended_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Session %s ended at %s", session_id, record.ended_at)


def log_tool_call(
    db: Session,
    session_id: str,
    tool_name: str,
    args: dict,
    result: dict,
) -> None:
    """Append a tool execution record to the tool_call_logs table.

    Also increments the tool_calls_made counter on the parent session.
    """
    log_record = ToolCallLogRecord(
        session_id=session_id,
        tool_name=tool_name,
        args=json.dumps(args),
        result=json.dumps(result),
        called_at=datetime.now(timezone.utc),
    )
    db.add(log_record)

    # Increment counter on the parent session
    session_record = (
        db.query(LectureSessionRecord)
        .filter(LectureSessionRecord.id == session_id)
        .first()
    )
    if session_record:
        session_record.tool_calls_made += 1

    db.commit()


def increment_api_calls(db: Session, session_id: str) -> None:
    """Increment the Gemini API call counter for a lecture session."""
    record = (
        db.query(LectureSessionRecord)
        .filter(LectureSessionRecord.id == session_id)
        .first()
    )
    if not record:
        logger.warning("increment_api_calls: session %s not found", session_id)
        return
    record.api_calls_used += 1
    db.commit()
