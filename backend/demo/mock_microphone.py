"""Mock microphone for DEMO_MODE.

Periodically injects pre-scripted student questions / comments into the
system so the Gemini orchestrator can react to them — no real microphone or
Whisper model needed.

``MockMicrophone`` is used by ``VoiceAgent`` when ``config.DEMO_MODE`` is
``True``.  After calling ``start(callback)``, a background timer thread fires
every 30–60 seconds and calls ``callback(text)`` with a randomly chosen
phrase from the built-in script.
"""

import logging
import random
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-scripted student phrases
# ---------------------------------------------------------------------------

SCRIPTED_QUESTIONS: list[str] = [
    "Can you explain that again?",
    "What about edge cases?",
    "How does this relate to real-world applications?",
    "Can you give an example?",
    "I'm confused about the last part.",
    "Why do we use this approach instead of a simpler one?",
    "What happens if the input is empty?",
    "Is this similar to what we covered last week?",
    "How would you test this in practice?",
    "Can you slow down a bit? That was a lot of information.",
]

# Interval range (seconds) between injected questions
_MIN_INTERVAL = 30.0
_MAX_INTERVAL = 60.0


class MockMicrophone:
    """Timer-based mock microphone that injects scripted student speech.

    Usage::

        def on_speech(text: str) -> None:
            voice_agent.inject_mock_speech(text)

        mic = MockMicrophone()
        mic.start(on_speech)
        # … lecture runs …
        mic.stop()
    """

    def __init__(self) -> None:
        self._callback: Optional[Callable[[str], None]] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, callback: Callable[[str], None]) -> None:
        """Start the background injection thread.

        Args:
            callback: Called with a scripted question string each time
                      the timer fires.  Typically points to
                      ``VoiceAgent.inject_mock_speech``.
        """
        if self._running:
            logger.warning("MockMicrophone: already running")
            return

        self._callback = callback
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(
            target=self._timer_loop, daemon=True, name="mock-mic"
        )
        self._thread.start()
        logger.info(
            "MockMicrophone: started (interval=%d–%ds)", _MIN_INTERVAL, _MAX_INTERVAL
        )

    def stop(self) -> None:
        """Signal the background thread to stop."""
        self._running = False
        self._stop_event.set()
        logger.info("MockMicrophone: stopped")

    @property
    def is_running(self) -> bool:
        """Return ``True`` if the injection thread is active."""
        return self._running

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _timer_loop(self) -> None:
        """Background thread: sleep → inject → repeat."""
        while self._running:
            # Wait for a random interval, but respond quickly to stop()
            interval = random.uniform(_MIN_INTERVAL, _MAX_INTERVAL)
            if self._stop_event.wait(timeout=interval):
                break

            if not self._running:
                break

            phrase = random.choice(SCRIPTED_QUESTIONS)
            logger.info("MockMicrophone: injecting %r", phrase)

            if self._callback:
                try:
                    self._callback(phrase)
                except Exception:
                    logger.exception("MockMicrophone: callback error")
