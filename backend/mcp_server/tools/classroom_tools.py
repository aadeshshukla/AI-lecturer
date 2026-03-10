"""Classroom management tools for the AI Autonomous Lecturer MCP server.

``scan_attendance`` delegates to the VisionAgent for real DeepFace face
recognition.  All other tools interact with lecture_state and broadcast
WebSocket events; student-device alert delivery is frontend-driven (PR3).
"""

import logging
from typing import List

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub
from backend.orchestrator.lecture_state import lecture_state

logger = logging.getLogger(__name__)


async def warn_student(
    student_id: str,
    reason: str,
    severity: str = "mild",
) -> dict:
    """Issue a warning to a student.

    Broadcasts a ``STUDENT_WARNED`` WebSocket event so the frontend can
    display the warning.  Increments the student's in-memory warning count.

    Args:
        student_id: ID of the student to warn.
        reason: Human-readable explanation for the warning.
        severity: "mild" | "moderate" | "severe".

    Returns:
        dict with keys ``status`` and ``student_name``.
    """
    student = lecture_state.students.get(student_id)
    student_name = student.name if student else student_id
    if student:
        student.warning_count += 1
    logger.info("warn_student: %s — %s (%s)", student_id, reason, severity)
    await ws_hub.broadcast(
        create_event(
            EventType.STUDENT_WARNED,
            {
                "student_id": student_id,
                "student_name": student_name,
                "reason": reason,
                "severity": severity,
            },
        )
    )
    return {"status": "warned", "student_name": student_name}


async def call_on_student(student_id: str, question: str) -> dict:
    """Ask a question directly to a student.

    Broadcasts a ``STUDENT_CALLED`` WebSocket event so the frontend can
    highlight the student and display the question.

    Args:
        student_id: ID of the student to call on.
        question: The question to pose.

    Returns:
        dict with keys ``status`` and ``student_name``.
    """
    student = lecture_state.students.get(student_id)
    student_name = student.name if student else student_id
    logger.info("call_on_student: %s — %s", student_id, question)
    await ws_hub.broadcast(
        create_event(
            EventType.STUDENT_CALLED,
            {
                "student_id": student_id,
                "student_name": student_name,
                "question": question,
            },
        )
    )
    return {"status": "called", "student_name": student_name}


async def scan_attendance() -> dict:
    """Run face recognition to determine which students are present.

    Delegates to ``vision_agent.scan_attendance()`` which captures a camera
    frame and matches faces against ``data/student_photos/`` using DeepFace.

    Returns:
        dict with keys ``present`` (list), ``absent`` (list), and
        ``unknown`` (int count of unrecognised faces).
    """
    from backend.agents.vision_agent import vision_agent  # local import

    logger.info("scan_attendance: delegating to VisionAgent")
    return await vision_agent.scan_attendance()


async def ask_class(question: str) -> dict:
    """Pose a question to the entire class.

    Broadcasts the question as a WebSocket event so the frontend can display
    it.  The VoiceAgent STT loop will capture any spoken responses and enqueue
    them as ``student_speech`` events for Gemini to react to.

    Args:
        question: The question to ask the whole class.

    Returns:
        dict with key ``status``.
    """
    logger.info("ask_class: %s", question)
    await ws_hub.broadcast(
        create_event(EventType.STUDENT_SPEECH, {"transcript": question, "from": "professor"})
    )
    return {"status": "asked"}
