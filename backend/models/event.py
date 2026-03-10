"""Classroom event data model for the AI Autonomous Lecturer System."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class ClassroomEvent:
    """Represents a real-time event that occurs in the classroom.

    Events are produced by the Vision Agent, Voice Agent, and other
    sensors, then injected into Gemini's context so it can react
    autonomously.

    Attributes:
        type: Category of event — e.g. "student_speech", "distraction",
            "question", "attendance_update".
        timestamp: UTC time the event was detected.
        data: Arbitrary key-value payload specific to the event type.
        handled: Whether Gemini has already acted on this event.
        injected_to_gemini: Whether this event has been included in a
            Gemini API call.
    """

    type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = field(default_factory=dict)
    handled: bool = False
    injected_to_gemini: bool = False
