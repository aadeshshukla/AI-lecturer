"""Lecture control tool stubs for the AI Autonomous Lecturer MCP server.

TODO PR2: Replace stubs with real lecture lifecycle management.
"""

import logging

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub
from backend.orchestrator.lecture_state import lecture_state

logger = logging.getLogger(__name__)


async def pause_lecture() -> dict:
    """Pause the ongoing lecture.

    Stub: will trigger full lifecycle pause in PR2.

    Returns:
        dict with key ``status``.
    """
    logger.info("[STUB] pause_lecture")
    await lecture_state.update_status("paused")
    await ws_hub.broadcast(create_event(EventType.LECTURE_PAUSED, {}))
    # TODO PR2: Pause Gemini loop + TTS + Vision Agent
    return {"status": "paused"}


async def end_lecture() -> dict:
    """Gracefully end the lecture session.

    Stub: will trigger full shutdown sequence in PR2.

    Returns:
        dict with key ``status``.
    """
    logger.info("[STUB] end_lecture")
    session = lecture_state.session
    api_calls = session.api_calls_used if session else 0
    tool_calls = session.tool_calls_made if session else 0
    await lecture_state.end_session()
    await ws_hub.broadcast(
        create_event(
            EventType.LECTURE_ENDED,
            {"duration_seconds": 0, "tool_calls": tool_calls, "api_calls_used": api_calls},
        )
    )
    # TODO PR2: Full shutdown sequence
    return {"status": "ended"}


async def set_difficulty(difficulty: str) -> dict:
    """Change the difficulty level of the ongoing lecture.

    Stub: will adjust Gemini system prompt in PR2.

    Args:
        difficulty: "beginner" | "intermediate" | "advanced".

    Returns:
        dict with key ``status``.
    """
    logger.info("[STUB] set_difficulty: %s", difficulty)
    # TODO PR2: Rebuild system prompt with new difficulty and reinject
    return {"status": "updated", "difficulty": difficulty}


async def get_class_status() -> dict:
    """Return a snapshot of the current classroom state.

    Stub: returns basic in-memory state.  PR2 will enrich with live
    attention scores from the Vision Agent.

    Returns:
        dict with keys ``distracted_students``, ``attentive_count``,
        ``time_elapsed``, and ``questions_pending``.
    """
    logger.info("[STUB] get_class_status")
    students = lecture_state.students
    distracted = [
        sid for sid, s in students.items() if s.attention_score < 0.3
    ]
    attentive = len(students) - len(distracted)
    pending_events = [
        e for e in lecture_state._pending_events if not e.handled  # noqa: SLF001
    ]
    status = {
        "distracted_students": distracted,
        "attentive_count": attentive,
        "time_elapsed": 0,
        "questions_pending": len(pending_events),
    }
    await ws_hub.broadcast(
        create_event(
            EventType.CLASS_STATUS_UPDATE,
            {
                "attentive_count": attentive,
                "distracted_count": len(distracted),
                "time_elapsed": 0,
            },
        )
    )
    return status
