"""MCP tool registry and execution engine for the AI Autonomous Lecturer.

This module:
  1. Defines all 18 Gemini function declarations in JSON schema format.
  2. Provides ``get_function_declarations()`` for building the Gemini model.
  3. Provides ``execute_tool()`` which routes a tool name to the correct
     async Python function, broadcasts WebSocket events, and logs to DB.
"""

import logging
from typing import Any, Dict, List

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini function declarations (JSON schema format)
# ---------------------------------------------------------------------------

_FUNCTION_DECLARATIONS: List[Dict[str, Any]] = [
    {
        "name": "speak",
        "description": "Convert text to speech and play on classroom speakers",
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
        "description": "Run face recognition on the camera feed to determine who is present",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "query_knowledge",
        "description": "Perform a semantic search over the lecture knowledge base (RAG)",
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
        "description": "Ask a question to the whole class and wait for raised hands or voices",
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
    """Return all Gemini function declarations for building the model.

    Returns:
        List of function declaration dicts in Gemini JSON schema format.
    """
    return _FUNCTION_DECLARATIONS


# ---------------------------------------------------------------------------
# Tool router
# ---------------------------------------------------------------------------

async def execute_tool(
    tool_name: str,
    args: Dict[str, Any],
    session_id: str | None = None,
    db=None,
) -> Dict[str, Any]:
    """Route a tool call to the correct async Python function.

    After execution:
      - Broadcasts a ``tool_called`` WebSocket event before execution.
      - Broadcasts a ``tool_result`` WebSocket event with the result.
      - Logs the call to the database if ``session_id`` and ``db`` are provided.

    Args:
        tool_name: Name of the tool as declared in Gemini function declarations.
        args: Keyword arguments extracted from Gemini's function_call.
        session_id: Optional active lecture session ID for DB logging.
        db: Optional SQLAlchemy Session for DB logging.

    Returns:
        Result dict from the tool function, or an error dict on failure.
    """
    # Lazy imports to avoid circular dependencies
    from backend.mcp_server.tools.speech_tools import speak, stop_speaking
    from backend.mcp_server.tools.board_tools import (
        write_on_board,
        clear_board,
        draw_diagram,
        highlight_board,
    )
    from backend.mcp_server.tools.slide_tools import advance_slide, go_to_slide, generate_slide
    from backend.mcp_server.tools.classroom_tools import (
        warn_student,
        call_on_student,
        scan_attendance,
        ask_class,
    )
    from backend.mcp_server.tools.knowledge_tools import query_knowledge
    from backend.mcp_server.tools.control_tools import (
        pause_lecture,
        end_lecture,
        set_difficulty,
        get_class_status,
    )

    _TOOL_MAP = {
        "speak": speak,
        "stop_speaking": stop_speaking,
        "write_on_board": write_on_board,
        "draw_diagram": draw_diagram,
        "clear_board": clear_board,
        "highlight_board": highlight_board,
        "advance_slide": advance_slide,
        "go_to_slide": go_to_slide,
        "generate_slide": generate_slide,
        "warn_student": warn_student,
        "call_on_student": call_on_student,
        "scan_attendance": scan_attendance,
        "query_knowledge": query_knowledge,
        "get_class_status": get_class_status,
        "pause_lecture": pause_lecture,
        "end_lecture": end_lecture,
        "set_difficulty": set_difficulty,
        "ask_class": ask_class,
    }

    # Broadcast pre-execution notification
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
    except Exception as exc:  # noqa: BLE001
        result = {"error": str(exc), "status": "error"}
        logger.exception("execute_tool: tool '%s' raised an exception", tool_name)

    # Broadcast result
    await ws_hub.broadcast(
        create_event(EventType.TOOL_RESULT, {"tool_name": tool_name, "result": result})
    )

    # Persist to database if context provided
    if session_id and db:
        try:
            from backend.database.sessions import log_tool_call
            log_tool_call(db, session_id, tool_name, args, result)
        except Exception:  # noqa: BLE001
            logger.warning("execute_tool: failed to log tool call to DB", exc_info=True)

    return result
