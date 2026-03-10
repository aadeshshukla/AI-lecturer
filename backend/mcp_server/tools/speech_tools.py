"""Speech tools for the AI Autonomous Lecturer MCP server.

Delegates to the VoiceAgent singleton for real Coqui TTS synthesis and
sounddevice audio playback.
"""

import logging

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub

logger = logging.getLogger(__name__)


async def speak(text: str, emotion: str = "neutral") -> dict:
    """Convert text to speech and play on classroom speakers.

    Delegates to ``voice_agent.speak()`` which handles Coqui TTS synthesis
    and audio playback via sounddevice.

    Args:
        text: The text to speak out loud.
        emotion: Tone of voice — "neutral" | "enthusiastic" | "serious" | "encouraging".

    Returns:
        dict with keys ``status`` and ``duration_estimate``.
    """
    from backend.agents.voice_agent import voice_agent  # local import to avoid circular deps

    return await voice_agent.speak(text, emotion)


async def stop_speaking() -> dict:
    """Interrupt current TTS playback immediately.

    Returns:
        dict with key ``status``.
    """
    from backend.agents.voice_agent import voice_agent

    return await voice_agent.stop_speaking()
