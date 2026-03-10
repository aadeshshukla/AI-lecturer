"""Classroom management tool stubs for the AI Autonomous Lecturer MCP server.

TODO PR2: Replace stubs with real face-recognition attendance scanning
and student-device alert delivery.
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

    Stub: will be replaced with real alert delivery in PR2.

    Args:
        student_id: ID of the student to warn.
        reason: Human-readable explanation for the warning.
        severity: "mild" | "moderate" | "severe".

    Returns:
        dict with keys ``status`` and ``student_name``.
    """
    student = lecture_state.students.get(student_id)
    student_name = student.name if student else student_id
    logger.info("[STUB] warn_student: %s — %s (%s)", student_id, reason, severity)
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
    # TODO PR2: Increment warning count in DB and send alert to student device
    return {"status": "warned", "student_name": student_name}


async def call_on_student(student_id: str, question: str) -> dict:
    """Ask a question directly to a student.

    Stub: will be replaced with real student-device alert in PR2.

    Args:
        student_id: ID of the student to call on.
        question: The question to pose.

    Returns:
        dict with keys ``status`` and ``student_name``.
    """
    student = lecture_state.students.get(student_id)
    student_name = student.name if student else student_id
    logger.info("[STUB] call_on_student: %s — %s", student_id, question)
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
    # TODO PR2: Send question alert to student-view page
    return {"status": "called", "student_name": student_name}


async def scan_attendance() -> dict:
    """Run face recognition to determine which students are present.

    Stub: will be replaced with real DeepFace / YOLOv8 scan in PR2.

    Returns:
        dict with keys ``present``, ``absent``, and ``unknown``.
    """
    logger.info("[STUB] scan_attendance")
    present: List[str] = []
    absent: List[str] = []
    for sid, student in lecture_state.students.items():
        if student.is_present:
            present.append(sid)
        else:
            absent.append(sid)
    await ws_hub.broadcast(
        create_event(
            EventType.ATTENDANCE_UPDATED,
            {"present": present, "absent": absent},
        )
    )
    # TODO PR2: Real camera capture + DeepFace recognition
    return {"present": present, "absent": absent, "unknown": 0}


async def ask_class(question: str) -> dict:
    """Pose a question to the entire class and wait for responses.

    Stub: will be replaced with real voice detection in PR2.

    Args:
        question: The question to ask the whole class.

    Returns:
        dict with key ``status``.
    """
    logger.info("[STUB] ask_class: %s", question)
    await ws_hub.broadcast(
        create_event(EventType.STUDENT_SPEECH, {"transcript": question, "from": "professor"})
    )
    # TODO PR2: Trigger STT listening for raised hands / voices
    return {"status": "asked"}
