"""Gemini API quota manager for the AI Autonomous Lecturer System.

Tracks daily API usage against the free tier limit of 250 requests/day
and broadcasts quota updates via WebSocket after each recorded call.
"""

import asyncio
import logging
import threading
from datetime import date

from backend.websocket.events import EventType, create_event

logger = logging.getLogger(__name__)


class QuotaManager:
    """Thread-safe manager for Gemini free-tier API call quota.

    The free tier allows 250 requests per day.  A safety margin of 10 calls
    is reserved for emergencies so normal operation is capped at 240.

    Attributes:
        DAILY_LIMIT: Total allowed API calls per day.
        SAFETY_MARGIN: Calls reserved for emergency use.
    """

    DAILY_LIMIT: int = 250
    SAFETY_MARGIN: int = 10

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls_today: int = 0
        self.reset_date: date = date.today()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def can_make_call(self) -> bool:
        """Return True if there is remaining quota for another API call."""
        self._check_reset()
        return self.calls_today < (self.DAILY_LIMIT - self.SAFETY_MARGIN)

    def record_call(self) -> None:
        """Increment the daily call counter and broadcast a quota_update event.

        This method is safe to call from any thread.
        """
        with self._lock:
            self._check_reset()
            self.calls_today += 1
            used = self.calls_today
            remaining = self.remaining()

        logger.info(
            "Gemini API call recorded — used: %d / %d (remaining: %d)",
            used,
            self.DAILY_LIMIT,
            remaining,
        )

        # Broadcast quota update asynchronously (non-blocking from threads)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast_quota(used, remaining))
        except RuntimeError:
            pass  # No running event loop — skip broadcast (e.g. during testing)

    def remaining(self) -> int:
        """Return the number of API calls remaining today."""
        self._check_reset()
        return max(0, self.DAILY_LIMIT - self.calls_today)

    def estimate_calls_for_lecture(self, duration_minutes: int) -> int:
        """Estimate the number of API calls a lecture of given length will use.

        The heuristic is approximately 1.5 calls per minute of lecture.

        Args:
            duration_minutes: Planned lecture duration in minutes.

        Returns:
            Estimated number of Gemini API requests.
        """
        return int(duration_minutes * 1.5)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_reset(self) -> None:
        """Reset counter if the calendar day has rolled over."""
        today = date.today()
        if today > self.reset_date:
            with self._lock:
                if today > self.reset_date:  # double-checked locking
                    logger.info(
                        "New day detected — resetting Gemini quota counter "
                        "(was %d calls)",
                        self.calls_today,
                    )
                    self.calls_today = 0
                    self.reset_date = today

    async def _broadcast_quota(self, used: int, remaining: int) -> None:
        """Broadcast a quota_update WebSocket event."""
        from backend.websocket.hub import ws_hub  # local import to avoid circularity

        event = create_event(
            EventType.QUOTA_UPDATE,
            {"used": used, "remaining": remaining, "limit": self.DAILY_LIMIT},
        )
        await ws_hub.broadcast(event)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
quota_manager = QuotaManager()
