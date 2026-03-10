"""Student CRUD operations for the AI Autonomous Lecturer database."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.database.db import StudentRecord
from backend.models.student import Student

logger = logging.getLogger(__name__)


def _to_model(record: StudentRecord) -> Student:
    """Convert a StudentRecord ORM object to a Student dataclass."""
    return Student(
        id=record.id,
        name=record.name,
        photo_path=record.photo_path,
        email=record.email,
        attention_score=record.attention_score,
        is_present=record.is_present,
        warning_count=record.warning_count,
        last_seen=record.last_seen,
    )


def create_student(db: Session, student: Student) -> Student:
    """Insert a new student record and return it.

    Args:
        db: Active SQLAlchemy session.
        student: Student dataclass to persist.

    Returns:
        The persisted Student.
    """
    record = StudentRecord(
        id=student.id,
        name=student.name,
        photo_path=student.photo_path,
        email=student.email,
        attention_score=student.attention_score,
        is_present=student.is_present,
        warning_count=student.warning_count,
        last_seen=student.last_seen,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info("Created student %s (%s)", student.id, student.name)
    return _to_model(record)


def get_student(db: Session, student_id: str) -> Optional[Student]:
    """Fetch a single student by ID, or None if not found."""
    record = db.query(StudentRecord).filter(StudentRecord.id == student_id).first()
    return _to_model(record) if record else None


def get_all_students(db: Session) -> List[Student]:
    """Return all students ordered by ID."""
    records = db.query(StudentRecord).order_by(StudentRecord.id).all()
    return [_to_model(r) for r in records]


def update_student(db: Session, student: Student) -> Student:
    """Overwrite all fields of an existing student record.

    Args:
        db: Active SQLAlchemy session.
        student: Student dataclass with updated values.

    Returns:
        The updated Student.

    Raises:
        ValueError: If no student with the given ID exists.
    """
    record = db.query(StudentRecord).filter(StudentRecord.id == student.id).first()
    if not record:
        raise ValueError(f"Student {student.id} not found")

    record.name = student.name
    record.photo_path = student.photo_path
    record.email = student.email
    record.attention_score = student.attention_score
    record.is_present = student.is_present
    record.warning_count = student.warning_count
    record.last_seen = student.last_seen
    db.commit()
    db.refresh(record)
    return _to_model(record)


def update_attendance(db: Session, student_id: str, is_present: bool) -> None:
    """Update a student's presence flag and refresh last_seen if present."""
    record = db.query(StudentRecord).filter(StudentRecord.id == student_id).first()
    if not record:
        logger.warning("update_attendance: student %s not found", student_id)
        return
    record.is_present = is_present
    if is_present:
        record.last_seen = datetime.now(timezone.utc)
    db.commit()


def update_attention_score(db: Session, student_id: str, score: float) -> None:
    """Update the rolling attention score (0.0–1.0) for a student."""
    record = db.query(StudentRecord).filter(StudentRecord.id == student_id).first()
    if not record:
        logger.warning("update_attention_score: student %s not found", student_id)
        return
    record.attention_score = max(0.0, min(1.0, score))
    db.commit()


def increment_warning_count(db: Session, student_id: str) -> None:
    """Atomically increment the warning counter for a student."""
    record = db.query(StudentRecord).filter(StudentRecord.id == student_id).first()
    if not record:
        logger.warning("increment_warning_count: student %s not found", student_id)
        return
    record.warning_count += 1
    db.commit()
