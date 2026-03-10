"""Speech tool stubs for the AI Autonomous Lecturer MCP server.

TODO PR2: Replace stubs with real Coqui TTS and audio playback
implementations using sounddevice / pyaudio.
"""

import asyncio
import logging

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub

logger = logging.getLogger(__name__)


async def speak(text: str, emotion: str = "neutral") -> dict:
    """Convert text to speech and play on classroom speakers.

    Stub: will be replaced with real Coqui TTS in PR2.

    Args:
        text: The text to speak out loud.
        emotion: Tone of voice — "neutral" | "enthusiastic" | "serious" | "encouraging".

    Returns:
        dict with keys ``status`` and ``duration_estimate``.
    """
    logger.info("[STUB] speak: %s (emotion=%s)", text, emotion)
    await ws_hub.broadcast(create_event(EventType.SPEAKING_START, {"text": text}))
    # TODO PR2: Real Coqui TTS implementation
    await asyncio.sleep(0.5)  # Simulate speaking delay
    await ws_hub.broadcast(create_event(EventType.SPEAKING_END, {"duration_ms": 500}))
    return {"status": "speaking", "duration_estimate": 0.5}


async def stop_speaking() -> dict:
    """Interrupt current TTS playback.

    Stub: will be replaced with real audio-thread interrupt in PR2.

    Returns:
        dict with key ``status``.
    """
    logger.info("[STUB] stop_speaking")
    await ws_hub.broadcast(create_event(EventType.SPEAKING_END, {"duration_ms": 0}))
    # TODO PR2: Kill TTS audio thread
    return {"status": "stopped"}
