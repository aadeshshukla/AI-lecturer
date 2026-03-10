"""Gemini 2.5 Flash autonomous orchestrator for the AI Autonomous Lecturer.

This module implements the brain of the lecturer system.  A single
``GeminiOrchestrator`` instance runs a continuous async loop that:

1. Reads pending classroom events from ``lecture_state``.
2. Builds a concise context message describing current classroom conditions.
3. Sends the message to the Gemini chat session.
4. Processes all function-call parts in the response by delegating to
   ``execute_tool`` from the MCP server.
5. Feeds every function response back to Gemini so it can react.
6. Respects the free-tier quota managed by ``quota_manager``.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import google.generativeai as genai

from backend import config
from backend.mcp_server.server import execute_tool, get_function_declarations
from backend.models.event import ClassroomEvent
from backend.models.lecture import LectureSession
from backend.orchestrator.lecture_state import lecture_state
from backend.orchestrator.quota_manager import quota_manager
from backend.orchestrator.system_prompt import build_system_prompt
from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub

logger = logging.getLogger(__name__)

# Maximum number of sequential function-call rounds per Gemini response.
_MAX_TOOL_ROUNDS: int = 10


class GeminiOrchestrator:
    """Autonomous Gemini 2.5 Flash orchestrator for the lecture session.

    One instance is created per application lifecycle and reused across
    multiple lecture sessions via ``start_lecture`` / ``stop_lecture``.

    Attributes:
        is_running: ``True`` while the autonomous loop is active.
        session_id: UUID of the currently active lecture session.
    """

    def __init__(self) -> None:
        """Configure the Gemini SDK and prepare instance variables."""
        genai.configure(api_key=config.GOOGLE_API_KEY)
        self._model_name: str = config.GEMINI_MODEL
        self._tools: list = [{"function_declarations": get_function_declarations()}]

        # These are set per lecture session.
        self._model: Optional[genai.GenerativeModel] = None
        self.chat: Optional[genai.ChatSession] = None  # type: ignore[type-arg]
        self.is_running: bool = False
        self.session_id: Optional[str] = None
        self._session_start: Optional[datetime] = None
        self._end_lecture_called: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_lecture(
        self,
        topic: str,
        duration_minutes: int,
        difficulty: str,
        student_count: int,
        session_id: str,
    ) -> None:
        """Start an autonomous lecture session.

        Builds the system prompt, initialises a new Gemini chat session,
        then enters the autonomous loop which runs until ``stop_lecture``
        is called or the ``end_lecture`` tool is invoked.

        Args:
            topic: Subject matter to be taught.
            duration_minutes: Planned maximum duration in minutes.
            difficulty: Complexity level — "beginner" | "intermediate" | "advanced".
            student_count: Expected number of students.
            session_id: UUID of the ``LectureSession`` in the database.
        """
        system_prompt = build_system_prompt(
            topic=topic,
            duration_minutes=duration_minutes,
            student_count=student_count,
            difficulty=difficulty,
        )

        self._model = genai.GenerativeModel(
            model_name=self._model_name,
            tools=self._tools,
            system_instruction=system_prompt,
        )
        self.chat = self._model.start_chat()
        self.is_running = True
        self.session_id = session_id
        self._session_start = datetime.now(timezone.utc)
        self._end_lecture_called = False

        logger.info(
            "GeminiOrchestrator: lecture started — session=%s, topic=%r, "
            "duration=%d min, difficulty=%s, students=%d",
            session_id,
            topic,
            duration_minutes,
            difficulty,
            student_count,
        )

        await ws_hub.broadcast(
            create_event(EventType.GEMINI_THINKING, {"status": "initialising"})
        )

        initial_message = (
            f"Begin the lecture now. "
            f"Topic: {topic}. "
            f"Duration: {duration_minutes} minutes. "
            f"Difficulty: {difficulty}. "
            f"Students expected: {student_count}. "
            f"Start with attendance."
        )

        await self._autonomous_loop(initial_message)

    async def stop_lecture(self) -> None:
        """Signal the autonomous loop to stop on the next iteration.

        This is a graceful shutdown; the current loop iteration completes
        before the loop exits.
        """
        logger.info("GeminiOrchestrator: stop_lecture() called")
        self.is_running = False

    # ------------------------------------------------------------------
    # Autonomous loop
    # ------------------------------------------------------------------

    async def _autonomous_loop(self, first_message: str) -> None:
        """Run the continuous reasoning-and-action loop.

        The loop sends a context message to Gemini on every iteration,
        processes any function calls in the response, and then sleeps
        briefly to pace API usage.

        Args:
            first_message: The initial prompt to kick off the lecture.
        """
        message = first_message
        is_first = True

        while self.is_running:
            # ---- Quota guard ----
            if not quota_manager.can_make_call():
                logger.warning(
                    "GeminiOrchestrator: daily quota exhausted — forcing end_lecture"
                )
                await self._force_end()
                break

            # ---- Build context (skip on first message) ----
            if not is_first:
                pending = await lecture_state.get_pending_events()
                message = self._build_context_message(pending)
            else:
                is_first = False

            try:
                await ws_hub.broadcast(
                    create_event(EventType.GEMINI_THINKING, {"status": "thinking"})
                )

                # Send message to Gemini
                response = self.chat.send_message(message)  # type: ignore[union-attr]
                quota_manager.record_call()

                # Update api_calls counter in session
                session: Optional[LectureSession] = lecture_state.session
                if session:
                    session.api_calls_used += 1

                # Process all function calls in the response
                stop = await self._process_response(response)
                if stop or self._end_lecture_called:
                    logger.info("GeminiOrchestrator: end_lecture detected — exiting loop")
                    self.is_running = False
                    break

            except Exception:
                logger.exception("GeminiOrchestrator: error in autonomous loop — continuing")

            await asyncio.sleep(config.GEMINI_LOOP_INTERVAL_SECONDS)

        logger.info("GeminiOrchestrator: autonomous loop exited")

    async def _process_response(self, response: genai.types.GenerateContentResponse) -> bool:  # type: ignore[name-defined]
        """Process all parts in a Gemini response.

        Handles function calls by executing the corresponding tool and
        feeding the result back to the model.  Text parts are logged as
        transcript entries.

        Args:
            response: The raw Gemini API response object.

        Returns:
            ``True`` if ``end_lecture`` was called and the loop should stop.
        """
        stop = False
        rounds = 0

        while rounds < _MAX_TOOL_ROUNDS:
            has_function_call = False

            for part in response.parts:
                # ---- Text parts ----
                if hasattr(part, "text") and part.text:
                    logger.debug("Gemini text: %s", part.text[:200])
                    await lecture_state.add_transcript_line(f"[GEMINI] {part.text}")

                # ---- Function-call parts ----
                if hasattr(part, "function_call") and part.function_call:
                    has_function_call = True
                    fn = part.function_call
                    fn_name: str = fn.name
                    fn_args: dict = dict(fn.args) if fn.args else {}

                    logger.info("Gemini tool call: %s(%s)", fn_name, fn_args)

                    # Detect end_lecture before executing so we can stop the loop
                    if fn_name == "end_lecture":
                        stop = True
                        self._end_lecture_called = True

                    # Execute the tool
                    try:
                        result = await execute_tool(
                            fn_name,
                            fn_args,
                            session_id=self.session_id or "",
                            db=None,
                        )
                    except Exception:
                        logger.exception("Tool execution failed: %s", fn_name)
                        result = {"error": f"Tool {fn_name} failed"}

                    # Update tool_calls counter
                    session = lecture_state.session
                    if session:
                        session.tool_calls_made += 1

                    # Feed function response back to Gemini
                    if quota_manager.can_make_call():
                        try:
                            response = self.chat.send_message(  # type: ignore[union-attr]
                                self._build_function_response(fn_name, result)
                            )
                            quota_manager.record_call()
                            if session:
                                session.api_calls_used += 1
                        except Exception:
                            logger.exception(
                                "Failed to send function response for: %s", fn_name
                            )
                            has_function_call = False

                    break  # Process one function call per pass; restart loop for next

            if not has_function_call:
                break  # No more function calls in this response

            rounds += 1

        return stop

    # ------------------------------------------------------------------
    # Context building
    # ------------------------------------------------------------------

    @staticmethod
    def _build_function_response(fn_name: str, result: dict) -> "genai.protos.Content":
        """Build a Gemini function-response Content object.

        Extracted into a helper to keep ``_process_response`` readable.

        Args:
            fn_name: The name of the function that was called.
            result: The dict result returned by the tool.

        Returns:
            A ``genai.protos.Content`` ready to send back to the chat session.
        """
        return genai.protos.Content(
            parts=[
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=fn_name,
                        response={"result": result},
                    )
                )
            ]
        )

    def _build_context_message(self, events: list[ClassroomEvent]) -> str:
        """Build a concise context message to inject into the Gemini chat.

        Includes elapsed time, student presence/attention, current slide,
        board state summary, and any pending classroom events.

        Args:
            events: List of unhandled ``ClassroomEvent`` objects from the queue.

        Returns:
            A short text string summarising current classroom conditions.
        """
        # Time elapsed
        if self._session_start:
            elapsed_seconds = (
                datetime.now(timezone.utc) - self._session_start
            ).total_seconds()
            elapsed_str = f"{int(elapsed_seconds // 60)}m {int(elapsed_seconds % 60)}s"
        else:
            elapsed_str = "unknown"

        # Student stats
        students = lecture_state.students
        present = [s for s in students.values() if s.is_present]
        distracted = [s for s in present if s.attention_score < config.DISTRACTION_THRESHOLD]
        avg_attention = (
            sum(s.attention_score for s in present) / len(present)
            if present
            else 1.0
        )

        # Slide and board
        slide_num = lecture_state.current_slide
        board_count = len(lecture_state.board_elements)

        # Quota
        remaining_calls = quota_manager.remaining()

        lines = [
            f"[SYSTEM UPDATE — {elapsed_str} elapsed]",
            f"Students present: {len(present)}/{len(students)} | "
            f"Average attention: {avg_attention:.0%} | "
            f"Distracted: {len(distracted)}",
            f"Current slide: {slide_num} | Board elements: {board_count}",
            f"API quota remaining: {remaining_calls}",
        ]

        if distracted:
            names = ", ".join(s.name for s in distracted)
            lines.append(f"⚠ Distracted students: {names}")

        if events:
            lines.append(f"\nPending events ({len(events)}):")
            for ev in events:
                if ev.type == "student_speech":
                    text = ev.data.get("text", "")
                    lines.append(f"  • Student said: \"{text}\"")
                elif ev.type == "distraction":
                    sid = ev.data.get("student_id", "unknown")
                    dur = ev.data.get("duration", 0)
                    student = students.get(sid)
                    name = student.name if student else sid
                    lines.append(f"  • {name} has been distracted for {dur}s")
                else:
                    lines.append(f"  • {ev.type}: {ev.data}")
        else:
            lines.append("\nNo pending events — continue the lecture.")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Emergency helpers
    # ------------------------------------------------------------------

    async def _force_end(self) -> None:
        """Force-end the lecture when quota is exhausted."""
        logger.warning("GeminiOrchestrator: forcing lecture end due to quota exhaustion")
        await lecture_state.update_status("ended")
        await ws_hub.broadcast(
            create_event(
                EventType.LECTURE_ENDED,
                {
                    "reason": "quota_exhausted",
                    "api_calls_used": (
                        lecture_state.session.api_calls_used
                        if lecture_state.session
                        else 0
                    ),
                },
            )
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
gemini_orchestrator = GeminiOrchestrator()
