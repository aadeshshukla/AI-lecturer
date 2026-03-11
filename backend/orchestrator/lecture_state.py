"""Shared lecture state singleton for the AI Autonomous Lecturer System.

All agents (Vision, Voice, Gemini orchestrator) read from and write to
this single LectureState instance, which is thread-safe and asyncio-safe.
"""

import asyncio
import logging
from collections import deque
from typing import Deque, Dict, List, Optional

from backend.models.event import ClassroomEvent
from backend.models.lecture import LectureSession
from backend.models.student import Student

logger = logging.getLogger(__name__)

# Maximum number of pending events kept in the queue at any time
_MAX_PENDING_EVENTS = 100
# Maximum transcript entries to keep in memory
_MAX_TRANSCRIPT_LINES = 500


class LectureState:
    """Thread-safe shared state accessible by every backend component.

    The state is partitioned into clearly-named sections:

    * **session** — the current LectureSession (None when idle).
    * **students** — dict of student_id → Student for the active session.
    * **events** — queue of ClassroomEvent objects waiting to be fed to Gemini.
    * **board_elements** — list of element dicts currently on the virtual board.
    * **transcript** — rolling deque of spoken/written transcript lines.
    * **current_slide** — the slide index the projector is currently showing.
    * **status** — human-readable system status string.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

        # Active lecture session
        self.session: Optional[LectureSession] = None

        # Students in the current session keyed by student_id
        self.students: Dict[str, Student] = {}

        # Pending classroom events waiting to be injected into Gemini
        self._pending_events: Deque[ClassroomEvent] = deque(
            maxlen=_MAX_PENDING_EVENTS
        )

        # Virtual whiteboard element list
        self.board_elements: List[dict] = []

        # Rolling transcript
        self.transcript: Deque[str] = deque(maxlen=_MAX_TRANSCRIPT_LINES)

        # Current slide index (1-based)
        self.current_slide: int = 1

        # Overall status string displayed on the dashboard
        self.status: str = "idle"

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    async def start_session(self, session: LectureSession) -> None:
        """Initialise state for a new lecture session."""
        async with self._lock:
            self.session = session
            self.status = "active"
            self.current_slide = 1
            self.board_elements = []
            self.transcript.clear()
            self._pending_events.clear()
            logger.info("Lecture state initialised for session %s", session.id)

    async def end_session(self) -> None:
        """Mark the session as ended."""
        async with self._lock:
            if self.session:
                self.session.status = "ended"
            self.status = "idle"
            logger.info("Lecture state cleared — session ended")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    async def update_status(self, status: str) -> None:
        """Update the human-readable status string."""
        async with self._lock:
            self.status = status
            if self.session:
                self.session.status = status

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    async def add_event(self, event: ClassroomEvent) -> None:
        """Enqueue a classroom event to be picked up by Gemini.

        Args:
            event: The ClassroomEvent to add.
        """
        async with self._lock:
            self._pending_events.append(event)
            logger.debug("Event enqueued: %s", event.type)

    async def get_pending_events(self) -> List[ClassroomEvent]:
        """Return all pending (unhandled) events and mark them as injected.

        Returns:
            List of ClassroomEvent objects that have not yet been sent to Gemini.
        """
        async with self._lock:
            pending = [e for e in self._pending_events if not e.injected_to_gemini]
            for event in pending:
                event.injected_to_gemini = True
            return pending

    async def mark_event_handled(self, event: ClassroomEvent) -> None:
        """Mark a specific event as handled by Gemini."""
        async with self._lock:
            event.handled = True

    # ------------------------------------------------------------------
    # Transcript
    # ------------------------------------------------------------------

    async def add_transcript_line(self, line: str) -> None:
        """Append a line to the rolling transcript."""
        async with self._lock:
            self.transcript.append(line)

    # ------------------------------------------------------------------
    # Slide tracking
    # ------------------------------------------------------------------

    async def set_slide(self, slide_number: int) -> None:
        """Update the current slide index."""
        async with self._lock:
            self.current_slide = slide_number

    # ------------------------------------------------------------------
    # Whiteboard
    # ------------------------------------------------------------------

    async def add_board_element(self, element: dict) -> None:
        """Append an element to the virtual whiteboard state."""
        async with self._lock:
            self.board_elements.append(element)

    async def clear_board(self) -> None:
        """Remove all elements from the virtual whiteboard state."""
        async with self._lock:
            self.board_elements.clear()

    # ------------------------------------------------------------------
    # Students
    # ------------------------------------------------------------------

    async def register_students(self, students: List[Student]) -> None:
        """Load a list of students into the active session."""
        async with self._lock:
            self.students = {s.id: s for s in students}

    async def update_student_attention(
        self, student_id: str, score: float
    ) -> None:
        """Update the attention score for a student in memory."""
        async with self._lock:
            if student_id in self.students:
                self.students[student_id].attention_score = max(0.0, min(1.0, score))

    async def update_student_presence(
        self, student_id: str, is_present: bool
    ) -> None:
        """Update the presence flag for a student in memory."""
        async with self._lock:
            if student_id in self.students:
                self.students[student_id].is_present = is_present

    async def increment_student_warnings(self, student_id: str) -> None:
        """Increment the warning counter for a student in memory."""
        async with self._lock:
            if student_id in self.students:
                self.students[student_id].warning_count += 1

    def get_unhandled_events(self) -> list:
        """Return unhandled events without acquiring the lock (read-only snapshot).

        Safe for use in status queries where stale data is acceptable.
        """
        return [e for e in self._pending_events if not e.handled]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
lecture_state = LectureState()
