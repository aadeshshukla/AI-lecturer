"""Lecture session data model for the AI Autonomous Lecturer System."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class LectureSession:
    """Represents a single autonomous lecture session.

    Attributes:
        id: UUID identifying this session.
        topic: Subject matter being taught.
        difficulty: Complexity level — "beginner", "intermediate", or "advanced".
        started_at: UTC timestamp when the lecture began.
        ended_at: UTC timestamp when the lecture ended, or None if still running.
        status: Current lifecycle state — "starting" | "active" | "paused" | "ended".
        duration_minutes: Planned maximum duration in minutes.
        slides_generated: Number of slides Gemini generated during the session.
        tool_calls_made: Total number of MCP tool calls executed.
        api_calls_used: Total Gemini API requests consumed (free-tier tracking).
        student_ids: IDs of students expected or detected in this session.
    """

    id: str
    topic: str
    difficulty: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str = "starting"
    duration_minutes: int = 45
    slides_generated: int = 0
    tool_calls_made: int = 0
    api_calls_used: int = 0
    student_ids: List[str] = field(default_factory=list)
