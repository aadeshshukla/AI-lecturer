"""Lecture control tools for the AI Autonomous Lecturer MCP server.

Implements lecture lifecycle management.  ``get_class_status`` is enriched
with live data from ``lecture_state`` and the ``AttentionAgent``.
"""

import logging
from datetime import datetime, timezone

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub
from backend.orchestrator.lecture_state import lecture_state

logger = logging.getLogger(__name__)


async def pause_lecture() -> dict:
    """Pause the ongoing lecture.

    Returns:
        dict with key ``status``.
    """
    logger.info("pause_lecture called")
    await lecture_state.update_status("paused")
    await ws_hub.broadcast(create_event(EventType.LECTURE_PAUSED, {}))
    return {"status": "paused"}


async def end_lecture() -> dict:
    """Gracefully end the lecture session.

    Updates state, broadcasts ``LECTURE_ENDED``, and signals the
    GeminiOrchestrator loop to stop.

    Returns:
        dict with key ``status``.
    """
    logger.info("end_lecture called")
    session = lecture_state.session

    duration_seconds = 0
    if session and session.started_at:
        duration_seconds = int(
            (datetime.now(timezone.utc) - session.started_at).total_seconds()
        )
    api_calls = session.api_calls_used if session else 0
    tool_calls = session.tool_calls_made if session else 0

    await lecture_state.end_session()
    await ws_hub.broadcast(
        create_event(
            EventType.LECTURE_ENDED,
            {
                "duration_seconds": duration_seconds,
                "tool_calls": tool_calls,
                "api_calls_used": api_calls,
            },
        )
    )
    return {"status": "ended"}


async def set_difficulty(difficulty: str) -> dict:
    """Change the difficulty level of the ongoing lecture.

    The new difficulty is stored in the session for context.  A future
    enhancement could rebuild the system prompt and inject it mid-session.

    Args:
        difficulty: "beginner" | "intermediate" | "advanced".

    Returns:
        dict with key ``status``.
    """
    logger.info("set_difficulty: %s", difficulty)
    session = lecture_state.session
    if session:
        session.difficulty = difficulty
    return {"status": "updated", "difficulty": difficulty}


async def get_class_status() -> dict:
    """Return a rich snapshot of the current classroom state.

    Pulls live attention data from the AttentionAgent and presence info
    from lecture_state to give Gemini an accurate picture of the class.

    Returns:
        dict with keys ``distracted_students``, ``attentive_count``,
        ``time_elapsed``, ``questions_pending``, ``average_attention``,
        ``trend``, and ``slide_number``.
    """
    from backend.agents.attention_agent import attention_agent  # local import

    logger.info("get_class_status called")
    students = lecture_state.students
    attention_summary = attention_agent.get_attention_summary()

    distracted = [
        sid for sid, s in students.items() if s.attention_score < 0.3 and s.is_present
    ]
    attentive_count = attention_summary.get("attentive_count", len(students) - len(distracted))

    # Calculate elapsed time
    session = lecture_state.session
    time_elapsed = 0
    if session and session.started_at:
        time_elapsed = int(
            (datetime.now(timezone.utc) - session.started_at).total_seconds()
        )

    pending_events = [
        e for e in lecture_state._pending_events if not e.handled  # noqa: SLF001
    ]

    status = {
        "distracted_students": distracted,
        "attentive_count": attentive_count,
        "time_elapsed": time_elapsed,
        "questions_pending": len(pending_events),
        "average_attention": attention_summary.get("average_attention", 1.0),
        "trend": attention_summary.get("trend", "stable"),
        "slide_number": lecture_state.current_slide,
        "most_distracted": attention_summary.get("most_distracted_name"),
    }

    await ws_hub.broadcast(
        create_event(
            EventType.CLASS_STATUS_UPDATE,
            {
                "attentive_count": attentive_count,
                "distracted_count": len(distracted),
                "time_elapsed": time_elapsed,
                "average_attention": status["average_attention"],
            },
        )
    )
    return status
