"""MCP tool registry and execution engine for the AI Autonomous Lecturer.

This module:
  1. Defines all function declarations in JSON schema format.
  2. Provides ``get_function_declarations()`` for building the model.
  3. Provides ``execute_tool()`` which routes a tool name to the correct
     async Python function and broadcasts WebSocket events.

All tool implementations are inlined here — no heavy external dependencies.
The browser handles TTS (Web Speech API), STT, and camera.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Function declarations (JSON schema format)
# ---------------------------------------------------------------------------

_FUNCTION_DECLARATIONS: List[Dict[str, Any]] = [
    {
        "name": "speak",
        "description": "Convert text to speech and play on classroom speakers via browser TTS",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to speak out loud",
                },
                "emotion": {
                    "type": "string",
                    "enum": ["neutral", "enthusiastic", "serious", "encouraging"],
                    "description": "Tone of voice",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "stop_speaking",
        "description": "Interrupt current TTS playback immediately",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "write_on_board",
        "description": "Write text or a LaTeX equation on the virtual whiteboard",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Text or LaTeX equation to write",
                },
                "position": {
                    "type": "string",
                    "description": "Position: 'auto' or '{x,y}' coordinates",
                },
                "style": {
                    "type": "string",
                    "enum": ["normal", "formula", "heading", "example"],
                    "description": "Visual style of the board element",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "draw_diagram",
        "description": "Draw a named diagram type on the virtual whiteboard",
        "parameters": {
            "type": "object",
            "properties": {
                "diagram_type": {
                    "type": "string",
                    "enum": ["flowchart", "mindmap", "timeline", "graph", "table", "formula"],
                    "description": "Type of diagram to draw",
                },
                "data": {
                    "type": "object",
                    "description": "Diagram-specific payload (nodes, edges, etc.)",
                },
            },
            "required": ["diagram_type", "data"],
        },
    },
    {
        "name": "clear_board",
        "description": "Clear all elements from the virtual whiteboard",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "highlight_board",
        "description": "Highlight a specific element on the virtual whiteboard",
        "parameters": {
            "type": "object",
            "properties": {
                "element_id": {
                    "type": "string",
                    "description": "ID of the board element to highlight",
                },
            },
            "required": ["element_id"],
        },
    },
    {
        "name": "advance_slide",
        "description": "Advance the projector to the next slide",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "go_to_slide",
        "description": "Jump to a specific slide number on the projector",
        "parameters": {
            "type": "object",
            "properties": {
                "slide_number": {
                    "type": "integer",
                    "description": "1-based target slide index",
                },
            },
            "required": ["slide_number"],
        },
    },
    {
        "name": "generate_slide",
        "description": "Generate a new slide on the fly from provided text",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Main body text for the slide",
                },
                "title": {
                    "type": "string",
                    "description": "Optional slide title",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "warn_student",
        "description": "Issue a warning to a student by ID with a reason",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "ID of the student to warn",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the warning",
                },
                "severity": {
                    "type": "string",
                    "enum": ["mild", "moderate", "severe"],
                    "description": "Severity level of the warning",
                },
            },
            "required": ["student_id", "reason"],
        },
    },
    {
        "name": "call_on_student",
        "description": "Ask a question to a specific student (triggers alert on their device)",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "ID of the student to call on",
                },
                "question": {
                    "type": "string",
                    "description": "Question to pose to the student",
                },
            },
            "required": ["student_id", "question"],
        },
    },
    {
        "name": "scan_attendance",
        "description": "Scan classroom to determine who is present (browser handles camera)",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "query_knowledge",
        "description": "Query the lecture knowledge base",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language query string",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of relevant chunks to return",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_class_status",
        "description": (
            "Returns current classroom snapshot: distracted students, "
            "attentive count, time elapsed, and pending questions"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "pause_lecture",
        "description": "Pause the ongoing lecture",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "end_lecture",
        "description": "Gracefully end the lecture session",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "set_difficulty",
        "description": "Change the difficulty level of the ongoing lecture",
        "parameters": {
            "type": "object",
            "properties": {
                "difficulty": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                    "description": "New difficulty level",
                },
            },
            "required": ["difficulty"],
        },
    },
    {
        "name": "ask_class",
        "description": "Ask a question to the whole class and wait for responses",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Question to pose to the entire class",
                },
            },
            "required": ["question"],
        },
    },
]


def get_function_declarations() -> List[Dict[str, Any]]:
    """Return all function declarations for building the model."""
    return _FUNCTION_DECLARATIONS


# ---------------------------------------------------------------------------
# Inlined tool implementations
# ---------------------------------------------------------------------------

async def _speak(text: str, emotion: str = "neutral") -> dict:
    """Broadcast speaking_start event — browser plays TTS via Web Speech API."""
    await ws_hub.broadcast(
        create_event(EventType.SPEAKING_START, {"text": text, "emotion": emotion})
    )
    # Estimate roughly 150 words/minute for speech duration
    word_count = len(text.split())
    duration_estimate = max(1.0, word_count / 2.5)
    return {"status": "speaking", "duration_estimate": duration_estimate}


async def _stop_speaking() -> dict:
    """Broadcast stop-speaking event."""
    await ws_hub.broadcast(create_event(EventType.SPEAKING_END, {}))
    return {"status": "stopped"}


async def _write_on_board(
    content: str,
    position: str = "auto",
    style: str = "normal",
) -> dict:
    """Broadcast board_write event — browser renders whiteboard content."""
    from backend.orchestrator.lecture_state import lecture_state  # local import

    element = {"content": content, "position": position, "style": style}
    await lecture_state.add_board_element(element)
    await ws_hub.broadcast(
        create_event(EventType.BOARD_WRITE, {"content": content, "position": position, "style": style})
    )
    return {"status": "written", "content": content}


async def _draw_diagram(diagram_type: str, data: dict) -> dict:
    """Broadcast board_draw event — browser renders the diagram."""
    from backend.orchestrator.lecture_state import lecture_state

    element = {"type": "diagram", "diagram_type": diagram_type, "data": data}
    await lecture_state.add_board_element(element)
    await ws_hub.broadcast(
        create_event(EventType.BOARD_DRAW, {"diagram_type": diagram_type, "data": data})
    )
    return {"status": "drawn", "diagram_type": diagram_type}


async def _clear_board() -> dict:
    """Clear whiteboard state and broadcast clear event."""
    from backend.orchestrator.lecture_state import lecture_state

    await lecture_state.clear_board()
    await ws_hub.broadcast(create_event(EventType.BOARD_CLEAR, {}))
    return {"status": "cleared"}


async def _highlight_board(element_id: str) -> dict:
    """Broadcast board_highlight event."""
    await ws_hub.broadcast(
        create_event(EventType.BOARD_HIGHLIGHT, {"element_id": element_id})
    )
    return {"status": "highlighted", "element_id": element_id}


async def _advance_slide() -> dict:
    """Advance slide counter and broadcast slide_advanced event."""
    from backend.orchestrator.lecture_state import lecture_state

    new_slide = lecture_state.current_slide + 1
    await lecture_state.set_slide(new_slide)
    await ws_hub.broadcast(
        create_event(EventType.SLIDE_ADVANCED, {"slide_number": new_slide})
    )
    return {"status": "advanced", "slide_number": new_slide}


async def _go_to_slide(slide_number: int) -> dict:
    """Jump to a specific slide and broadcast slide_advanced event."""
    from backend.orchestrator.lecture_state import lecture_state

    await lecture_state.set_slide(slide_number)
    await ws_hub.broadcast(
        create_event(EventType.SLIDE_ADVANCED, {"slide_number": slide_number})
    )
    return {"status": "navigated", "slide_number": slide_number}


async def _generate_slide(content: str, title: str = "") -> dict:
    """Generate a new slide and broadcast slide_advanced event."""
    from backend.orchestrator.lecture_state import lecture_state

    new_slide = lecture_state.current_slide + 1
    await lecture_state.set_slide(new_slide)
    await ws_hub.broadcast(
        create_event(
            EventType.SLIDE_ADVANCED,
            {"slide_number": new_slide, "content": content, "title": title},
        )
    )
    return {"status": "generated", "slide_number": new_slide}


async def _warn_student(student_id: str, reason: str, severity: str = "mild") -> dict:
    """Broadcast student_warned event and increment warning counter."""
    from backend.orchestrator.lecture_state import lecture_state

    await lecture_state.increment_student_warnings(student_id)

    await ws_hub.broadcast(
        create_event(
            EventType.STUDENT_WARNED,
            {"student_id": student_id, "reason": reason, "severity": severity},
        )
    )
    return {"status": "warned", "student_id": student_id}


async def _call_on_student(student_id: str, question: str) -> dict:
    """Broadcast student_called event."""
    await ws_hub.broadcast(
        create_event(
            EventType.STUDENT_CALLED,
            {"student_id": student_id, "question": question},
        )
    )
    return {"status": "called", "student_id": student_id, "question": question}


async def _scan_attendance() -> dict:
    """Return all known students as present (browser handles camera detection)."""
    from backend.orchestrator.lecture_state import lecture_state

    students = lecture_state.students
    present_ids = list(students.keys())

    # Mark all as present in memory
    for s in students.values():
        s.is_present = True

    await ws_hub.broadcast(
        create_event(
            EventType.ATTENDANCE_UPDATED,
            {"present_ids": present_ids, "total": len(present_ids)},
        )
    )
    return {"status": "scanned", "present": present_ids, "count": len(present_ids)}


async def _query_knowledge(query: str, top_k: int = 3) -> dict:
    """Return a stub response — no RAG in lightweight mode."""
    return {
        "status": "ok",
        "results": [],
        "message": "Knowledge base not loaded. Use your own knowledge to answer.",
        "query": query,
    }


async def _get_class_status() -> dict:
    """Return a classroom status snapshot from in-memory state."""
    from backend.orchestrator.lecture_state import lecture_state

    students = lecture_state.students
    present = [s for s in students.values() if s.is_present]
    distracted = [s for s in present if s.attention_score < 0.3]
    avg_attention = (
        sum(s.attention_score for s in present) / len(present) if present else 1.0
    )

    session = lecture_state.session
    time_elapsed = 0
    if session and session.started_at:
        started = session.started_at
        if started.tzinfo is None:
            from datetime import timezone as _tz
            started = started.replace(tzinfo=_tz.utc)
        time_elapsed = int((datetime.now(timezone.utc) - started).total_seconds())

    pending_events = lecture_state.get_unhandled_events()

    status = {
        "distracted_students": [s.id for s in distracted],
        "attentive_count": len(present) - len(distracted),
        "time_elapsed": time_elapsed,
        "questions_pending": len(pending_events),
        "average_attention": round(avg_attention, 3),
        "slide_number": lecture_state.current_slide,
    }

    await ws_hub.broadcast(
        create_event(
            EventType.CLASS_STATUS_UPDATE,
            {
                "attentive_count": status["attentive_count"],
                "distracted_count": len(distracted),
                "time_elapsed": time_elapsed,
                "average_attention": avg_attention,
            },
        )
    )
    return status


async def _pause_lecture() -> dict:
    """Pause the lecture via state update."""
    from backend.orchestrator.lecture_state import lecture_state

    await lecture_state.update_status("paused")
    await ws_hub.broadcast(create_event(EventType.LECTURE_PAUSED, {}))
    return {"status": "paused"}


async def _end_lecture() -> dict:
    """End the lecture session."""
    from backend.orchestrator.lecture_state import lecture_state

    session = lecture_state.session
    duration_seconds = 0
    if session and session.started_at:
        started = session.started_at
        if started.tzinfo is None:
            from datetime import timezone as _tz
            started = started.replace(tzinfo=_tz.utc)
        duration_seconds = int((datetime.now(timezone.utc) - started).total_seconds())

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


async def _set_difficulty(difficulty: str) -> dict:
    """Update the difficulty level in the session."""
    from backend.orchestrator.lecture_state import lecture_state

    session = lecture_state.session
    if session:
        session.difficulty = difficulty
    return {"status": "updated", "difficulty": difficulty}


async def _ask_class(question: str) -> dict:
    """Broadcast a class-wide question event."""
    await ws_hub.broadcast(
        create_event("ask_class", {"question": question})
    )
    return {"status": "asked", "question": question}


# ---------------------------------------------------------------------------
# Tool router
# ---------------------------------------------------------------------------

_TOOL_MAP: Dict[str, Any] = {
    "speak": _speak,
    "stop_speaking": _stop_speaking,
    "write_on_board": _write_on_board,
    "draw_diagram": _draw_diagram,
    "clear_board": _clear_board,
    "highlight_board": _highlight_board,
    "advance_slide": _advance_slide,
    "go_to_slide": _go_to_slide,
    "generate_slide": _generate_slide,
    "warn_student": _warn_student,
    "call_on_student": _call_on_student,
    "scan_attendance": _scan_attendance,
    "query_knowledge": _query_knowledge,
    "get_class_status": _get_class_status,
    "pause_lecture": _pause_lecture,
    "end_lecture": _end_lecture,
    "set_difficulty": _set_difficulty,
    "ask_class": _ask_class,
}


async def execute_tool(
    tool_name: str,
    args: Dict[str, Any],
    session_id: str | None = None,
) -> Dict[str, Any]:
    """Route a tool call to the correct async Python function.

    Args:
        tool_name: Name of the tool as declared in function declarations.
        args: Keyword arguments for the tool function.
        session_id: Optional active lecture session ID (unused, kept for compat).

    Returns:
        Result dict from the tool function, or an error dict on failure.
    """
    # Guard against None args
    args = args if isinstance(args, dict) else {}

    await ws_hub.broadcast(
        create_event(EventType.TOOL_CALLED, {"tool_name": tool_name, "args": args})
    )

    if tool_name not in _TOOL_MAP:
        error_result: Dict[str, Any] = {
            "error": f"Unknown tool: {tool_name}",
            "status": "error",
        }
        logger.error("execute_tool: unknown tool '%s'", tool_name)
        await ws_hub.broadcast(
            create_event(EventType.TOOL_RESULT, {"tool_name": tool_name, "result": error_result})
        )
        return error_result

    try:
        result = await _TOOL_MAP[tool_name](**args)
    except Exception as exc:
        result = {"error": str(exc), "status": "error"}
        logger.exception("execute_tool: tool '%s' raised an exception", tool_name)

    await ws_hub.broadcast(
        create_event(EventType.TOOL_RESULT, {"tool_name": tool_name, "result": result})
    )

    return result
