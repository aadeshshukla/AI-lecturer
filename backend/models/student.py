"""Student data model for the AI Autonomous Lecturer System."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Student:
    """Represents a student enrolled in the classroom.

    Attributes:
        id: Unique student identifier (e.g. "s001").
        name: Full display name.
        photo_path: Path to the student's face photo used for recognition.
        email: Student email address.
        attention_score: Rolling average attention level from 0.0 (distracted)
            to 1.0 (fully attentive).
        is_present: Whether the student was detected present in this session.
        warning_count: Number of warnings issued during the current session.
        last_seen: Timestamp of the most recent face detection.
    """

    id: str
    name: str
    photo_path: str
    email: str
    attention_score: float = 1.0
    is_present: bool = False
    warning_count: int = 0
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
