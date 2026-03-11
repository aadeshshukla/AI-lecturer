"""Virtual whiteboard tool stubs for the AI Autonomous Lecturer MCP server.

TODO PR2: Replace stubs with real React + Konva.js board control
implementations.
"""

import logging
import uuid

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub
from backend.orchestrator.lecture_state import lecture_state

logger = logging.getLogger(__name__)


async def write_on_board(
    content: str,
    position: str = "auto",
    style: str = "normal",
) -> dict:
    """Write text or an equation on the virtual whiteboard.

    Stub: will be replaced with real WebSocket-driven Konva canvas update in PR2.

    Args:
        content: Text or LaTeX equation to write.
        position: "auto" or "{x,y}" coordinate string.
        style: Visual style — "normal" | "formula" | "heading" | "example".

    Returns:
        dict with keys ``status`` and ``element_id``.
    """
    element_id = str(uuid.uuid4())
    logger.info("[STUB] write_on_board: %s (style=%s, pos=%s)", content, style, position)
    if position == "auto":
        board_index = len(lecture_state.board_elements)
        normalized_position = {"x": 20, "y": 20 + board_index * 60}
    else:
        normalized_position = position

    element = {
        "id": element_id,
        "type": style if style in {"heading", "example", "formula"} else "text",
        "content": content,
        "style": {"variant": style},
        "position": normalized_position,
    }
    await lecture_state.add_board_element(element)
    await ws_hub.broadcast(
        create_event(
            EventType.BOARD_WRITE,
            {
                "id": element_id,
                "element_id": element_id,
                "element_type": element["type"],
                "content": content,
                "style": element["style"],
                "position": normalized_position,
            },
        )
    )
    # TODO PR2: Real Konva canvas command
    return {"status": "written", "element_id": element_id}


async def clear_board() -> dict:
    """Clear all elements from the virtual whiteboard.

    Stub: will be replaced with real canvas clear command in PR2.

    Returns:
        dict with key ``status``.
    """
    logger.info("[STUB] clear_board")
    await lecture_state.clear_board()
    await ws_hub.broadcast(create_event(EventType.BOARD_CLEAR, {}))
    # TODO PR2: Real Konva canvas clear
    return {"status": "cleared"}


async def draw_diagram(diagram_type: str, data: dict) -> dict:
    """Draw a named diagram on the virtual whiteboard.

    Stub: will be replaced with real diagram-rendering logic in PR2.

    Args:
        diagram_type: Type of diagram — "flowchart" | "mindmap" | "timeline" |
            "graph" | "table" | "formula".
        data: Diagram-specific payload (e.g. nodes and edges for a flowchart).

    Returns:
        dict with keys ``status`` and ``element_id``.
    """
    element_id = str(uuid.uuid4())
    logger.info("[STUB] draw_diagram: type=%s", diagram_type)
    labels = data.get("labels") if isinstance(data, dict) else None
    content = labels if isinstance(labels, list) else data
    element = {
        "id": element_id,
        "type": "diagram",
        "content": content,
        "style": {"diagram_type": diagram_type},
        "position": {"x": 20, "y": 20 + len(lecture_state.board_elements) * 70},
    }
    await lecture_state.add_board_element(element)
    await ws_hub.broadcast(
        create_event(
            EventType.BOARD_DRAW,
            {
                "id": element_id,
                "element_id": element_id,
                "element_type": "diagram",
                "diagram_type": diagram_type,
                "content": content,
                "style": element["style"],
                "position": element["position"],
                "diagram_data": data,
            },
        )
    )
    # TODO PR2: Real diagram rendering
    return {"status": "drawn", "element_id": element_id}


async def highlight_board(element_id: str) -> dict:
    """Highlight a specific element on the virtual whiteboard.

    Stub: will be replaced with real canvas pulse animation in PR2.

    Args:
        element_id: The ID of the board element to highlight.

    Returns:
        dict with key ``status``.
    """
    logger.info("[STUB] highlight_board: element_id=%s", element_id)
    await ws_hub.broadcast(
        create_event(EventType.BOARD_HIGHLIGHT, {"element_id": element_id})
    )
    # TODO PR2: Real canvas highlight animation
    return {"status": "highlighted"}
