"""Slide control tool stubs for the AI Autonomous Lecturer MCP server.

TODO PR2: Replace stubs with real reveal.js slide controller.
"""

import logging

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub
from backend.orchestrator.lecture_state import lecture_state

logger = logging.getLogger(__name__)


async def advance_slide() -> dict:
    """Advance to the next slide on the projector.

    Stub: will be replaced with real reveal.js navigation in PR2.

    Returns:
        dict with keys ``status`` and ``slide_number``.
    """
    logger.info("[STUB] advance_slide")
    new_slide = lecture_state.current_slide + 1
    await lecture_state.set_slide(new_slide)
    await ws_hub.broadcast(
        create_event(EventType.SLIDE_ADVANCED, {"slide_number": new_slide, "total_slides": 0})
    )
    # TODO PR2: Real reveal.js next-slide command
    return {"status": "advanced", "slide_number": new_slide}


async def go_to_slide(slide_number: int) -> dict:
    """Jump to a specific slide number on the projector.

    Stub: will be replaced with real reveal.js navigation in PR2.

    Args:
        slide_number: 1-based target slide index.

    Returns:
        dict with keys ``status`` and ``slide_number``.
    """
    logger.info("[STUB] go_to_slide: %d", slide_number)
    await lecture_state.set_slide(slide_number)
    await ws_hub.broadcast(
        create_event(
            EventType.SLIDE_ADVANCED,
            {"slide_number": slide_number, "total_slides": 0},
        )
    )
    # TODO PR2: Real reveal.js slide jump
    return {"status": "navigated", "slide_number": slide_number}


async def generate_slide(content: str, title: str = "") -> dict:
    """Generate a new slide on the fly from provided text.

    Stub: will be replaced with real slide HTML generator in PR2.

    Args:
        content: Main body text for the slide.
        title: Optional slide title.

    Returns:
        dict with keys ``status`` and ``slide_number``.
    """
    logger.info("[STUB] generate_slide: title=%s", title)
    new_slide = lecture_state.current_slide + 1
    await lecture_state.set_slide(new_slide)
    await ws_hub.broadcast(
        create_event(
            EventType.SLIDE_ADVANCED,
            {"slide_number": new_slide, "total_slides": 0, "title": title},
        )
    )
    # TODO PR2: Real HTML slide generation and reveal.js injection
    return {"status": "generated", "slide_number": new_slide}
