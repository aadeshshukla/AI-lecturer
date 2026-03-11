"""WebSocket event type definitions for the AI Autonomous Lecturer System.

All real-time communication between the backend and frontend uses the
WSEvent dataclass defined here.  Use create_event() as a convenience
factory so every event automatically gets an ISO-8601 timestamp.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict


class EventType(str, Enum):
    """Enumeration of all WebSocket event types."""

    # Lecture lifecycle
    LECTURE_STARTED = "lecture_started"
    LECTURE_PAUSED = "lecture_paused"
    LECTURE_RESUMED = "lecture_resumed"
    LECTURE_ENDED = "lecture_ended"

    # Speech
    SPEAKING_START = "speaking_start"
    SPEAKING_END = "speaking_end"

    # Virtual whiteboard
    BOARD_WRITE = "board_write"
    BOARD_CLEAR = "board_clear"
    BOARD_DRAW = "board_draw"
    BOARD_HIGHLIGHT = "board_highlight"

    # Slides
    SLIDE_ADVANCED = "slide_advanced"

    # Classroom management
    STUDENT_WARNED = "student_warned"
    STUDENT_CALLED = "student_called"
    STUDENT_DISTRACTED = "student_distracted"
    ATTENDANCE_UPDATED = "attendance_updated"
    STUDENT_SPEECH = "student_speech"

    # AI / system
    GEMINI_THINKING = "gemini_thinking"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    CLASS_STATUS_UPDATE = "class_status_update"
    QUOTA_UPDATE = "quota_update"


@dataclass
class WSEvent:
    """A single WebSocket broadcast event.

    Attributes:
        type: Event category (one of the EventType enum values).
        timestamp: ISO-8601 UTC timestamp set at creation time.
        data: Arbitrary payload specific to the event type.
    """

    type: str
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the event to a plain dictionary for JSON encoding."""
        return asdict(self)


def create_event(event_type: str, data: Dict[str, Any] | None = None) -> WSEvent:
    """Factory function that stamps an event with the current UTC time.

    Args:
        event_type: One of the EventType enum values (or a plain string).
        data: Optional payload dictionary.

    Returns:
        A fully-populated WSEvent ready to broadcast.
    """
    return WSEvent(
        type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        data=data or {},
    )
