"""Groq (Llama 3.3) autonomous orchestrator for the AI Autonomous Lecturer.

Drop-in replacement for the Gemini orchestrator using Groq's free tier:
  - 14,400 requests/day (vs Gemini's 250/day)
  - llama-3.3-70b-versatile supports full function calling
  - No credit card required — sign up at https://console.groq.com

The public interface (GeminiOrchestrator class, gemini_orchestrator singleton)
is kept identical so no other file needs to change.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from groq import AsyncGroq

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

# Keep only this many recent turns in history to avoid hitting token limits.
_MAX_HISTORY_MESSAGES: int = 40
_MIN_END_LECTURE_SECONDS: int = 120


def _wrap_tools(declarations: list[dict]) -> list[dict]:
    """Convert raw function-declaration dicts to OpenAI-compatible tool format."""
    return [{"type": "function", "function": decl} for decl in declarations]


class GeminiOrchestrator:
    """Groq/Llama autonomous orchestrator.

    The class is intentionally named GeminiOrchestrator to preserve API
    compatibility with the rest of the codebase (main.py imports it by this name).

    Attributes:
        is_running: True while the autonomous loop is active.
        session_id: UUID of the currently active lecture session.
    """

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=config.GROQ_API_KEY)
        self._model_name: str = config.GROQ_MODEL
        self._tools: list[dict] = _wrap_tools(get_function_declarations())

        # Conversation history — rebuilt fresh for each lecture session.
        self._messages: list[dict] = []

        # Kept for compatibility; not used by Groq path.
        self.chat = None

        self.is_running: bool = False
        self.session_id: Optional[str] = None
        self._session_start: Optional[datetime] = None
        self._target_duration_minutes: int = 0
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
        """Start an autonomous lecture session."""
        system_prompt = build_system_prompt(
            topic=topic,
            duration_minutes=duration_minutes,
            student_count=student_count,
            difficulty=difficulty,
        )

        # Fresh conversation for each session
        self._messages = [{"role": "system", "content": system_prompt}]
        self.is_running = True
        self.session_id = session_id
        self._session_start = datetime.now(timezone.utc)
        self._target_duration_minutes = duration_minutes
        self._end_lecture_called = False

        logger.info(
            "GeminiOrchestrator (Groq): lecture started — session=%s, topic=%r, "
            "duration=%d min, difficulty=%s, students=%d",
            session_id, topic, duration_minutes, difficulty, student_count,
        )

        await ws_hub.broadcast(
            create_event(EventType.GEMINI_THINKING, {"status": "initialising"})
        )

        first_message = (
            f"Begin the lecture now. "
            f"Topic: {topic}. "
            f"Duration: {duration_minutes} minutes. "
            f"Difficulty: {difficulty}. "
            f"Students expected: {student_count}. "
            f"Start with a brief introduction to the topic."
        )
        await self._autonomous_loop(first_message)

    async def stop_lecture(self) -> None:
        """Signal the autonomous loop to stop."""
        logger.info("GeminiOrchestrator.stop_lecture() called")
        self.is_running = False

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    async def _autonomous_loop(self, first_message: str) -> None:
        """Continuous reasoning-and-action loop."""
        self._messages.append({"role": "user", "content": first_message})
        is_first = True

        while self.is_running:
            if not quota_manager.can_make_call():
                logger.warning("GeminiOrchestrator: quota exhausted — forcing end")
                await self._force_end()
                break

            if not is_first:
                pending = await lecture_state.get_pending_events()
                self._messages.append({
                    "role": "user",
                    "content": self._build_context_message(pending),
                })
            else:
                is_first = False

            try:
                await ws_hub.broadcast(
                    create_event(EventType.GEMINI_THINKING, {"status": "thinking"})
                )

                text, tool_calls = await self._call_model()
                quota_manager.record_call()

                session: Optional[LectureSession] = lecture_state.session
                if session:
                    session.api_calls_used += 1

                if text:
                    logger.debug("Groq text: %s", text[:200])
                    await lecture_state.add_transcript_line(f"[AI] {text}")

                stop = await self._process_tool_calls(tool_calls)
                if stop or self._end_lecture_called:
                    logger.info("GeminiOrchestrator: end_lecture — exiting loop")
                    self.is_running = False
                    break

            except Exception as exc:
                err_str = str(exc)
                if await self._recover_from_tool_use_failed(exc):
                    await asyncio.sleep(config.GEMINI_LOOP_INTERVAL_SECONDS)
                    continue
                if "429" in err_str or "rate_limit" in err_str.lower():
                    logger.warning(
                        "GeminiOrchestrator: 429 rate-limited — backing off 60 s"
                    )
                    await ws_hub.broadcast(
                        create_event(
                            EventType.GEMINI_THINKING,
                            {"status": "rate_limited", "retry_in": 60},
                        )
                    )
                    await asyncio.sleep(60)
                    continue
                logger.exception("GeminiOrchestrator: error in autonomous loop — continuing")

            await asyncio.sleep(config.GEMINI_LOOP_INTERVAL_SECONDS)

        logger.info("GeminiOrchestrator: autonomous loop exited")

    async def _call_model(self) -> tuple[str | None, list]:
        """Send the current message history to Groq and return (text, tool_calls)."""
        # Keep system message + last N turns to avoid token overflow
        system_msg = self._messages[0]
        tail = self._messages[1:]
        if len(tail) > _MAX_HISTORY_MESSAGES:
            tail = tail[-_MAX_HISTORY_MESSAGES:]
        messages = [system_msg] + tail

        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            tools=self._tools,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        # Persist assistant turn in full history
        entry: dict = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        self._messages.append(entry)
        return msg.content, msg.tool_calls or []

    async def _recover_from_tool_use_failed(self, exc: Exception) -> bool:
        """Recover from Groq `tool_use_failed` by parsing failed_generation.

        Some Groq responses return a malformed function-call string inside the
        error payload (e.g. ``<function=speak={...}</function>``). This helper
        extracts the function name and JSON args and executes the tool directly.
        """
        error_text = str(exc)
        if "tool_use_failed" not in error_text:
            return False

        failed_generation = ""
        err_body = getattr(exc, "body", None)
        if isinstance(err_body, dict):
            failed_generation = (
                err_body.get("error", {}).get("failed_generation", "") or ""
            )
        if not failed_generation:
            fg_match = re.search(r"'failed_generation':\s*'(?P<fg>.*?)'\s*\}\}$", error_text)
            if fg_match:
                failed_generation = fg_match.group("fg")
        if not failed_generation:
            failed_generation = error_text

        match = re.search(
            r"<function=(?P<name>[a-zA-Z0-9_]+)=(?P<args>\{.*?\})</function>",
            failed_generation,
            flags=re.DOTALL,
        )
        if not match:
            match = re.search(
                r"<function=(?P<name>[a-zA-Z0-9_]+)[^\{]*(?P<args>\{.*?\})</function>",
                failed_generation,
                flags=re.DOTALL,
            )
        if not match:
            logger.warning("tool_use_failed received, but no recoverable function payload")
            return False

        fn_name = match.group("name")
        raw_args = match.group("args").replace("\\'", "'")
        try:
            fn_args = json.loads(raw_args)
        except json.JSONDecodeError:
            # Fallback for malformed JSON-like payloads: recover common speak() case.
            if fn_name == "speak":
                text_match = re.search(r'"text"\s*:\s*"(?P<text>.*?)"', raw_args, flags=re.DOTALL)
                emotion_match = re.search(
                    r'"emotion"\s*:\s*"(?P<emotion>.*?)"', raw_args, flags=re.DOTALL
                )
                if text_match:
                    fn_args = {
                        "text": text_match.group("text").replace('\\"', '"'),
                        "emotion": (
                            emotion_match.group("emotion") if emotion_match else "neutral"
                        ),
                    }
                else:
                    logger.warning("tool_use_failed payload had invalid JSON args")
                    return False
            else:
                logger.warning("tool_use_failed payload had invalid JSON args")
                return False

        logger.warning("Recovered malformed tool call from Groq error: %s", fn_name)
        try:
            await execute_tool(fn_name, fn_args, session_id=self.session_id or "", db=None)
        except Exception:
            logger.exception("Recovered tool execution failed: %s", fn_name)
            return False

        session = lecture_state.session
        if session:
            session.tool_calls_made += 1
        return True

    async def _process_tool_calls(self, tool_calls: list) -> bool:
        """Execute every tool call, add results to history, get continuation.

        Returns True if end_lecture was called.
        """
        if not tool_calls:
            return False

        stop = False
        for tc in tool_calls:
            fn_name: str = tc.function.name
            try:
                fn_args: dict = json.loads(tc.function.arguments)
            except Exception:
                fn_args = {}

            logger.info("Tool call: %s(%s)", fn_name, fn_args)

            if fn_name == "end_lecture":
                elapsed_seconds = 0
                if self._session_start:
                    elapsed_seconds = int(
                        (datetime.now(timezone.utc) - self._session_start).total_seconds()
                    )
                min_runtime_seconds = min(
                    _MIN_END_LECTURE_SECONDS,
                    max(30, int(self._target_duration_minutes * 60 * 0.2)),
                )
                if elapsed_seconds < min_runtime_seconds:
                    logger.info(
                        "Ignoring premature end_lecture at %ss (min=%ss)",
                        elapsed_seconds,
                        min_runtime_seconds,
                    )
                    self._messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(
                            {
                                "status": "ignored",
                                "reason": "lecture_too_early_to_end",
                                "elapsed_seconds": elapsed_seconds,
                                "min_runtime_seconds": min_runtime_seconds,
                            }
                        ),
                    })
                    continue

                stop = True
                self._end_lecture_called = True

            try:
                result = await execute_tool(
                    fn_name, fn_args,
                    session_id=self.session_id or "",
                    db=None,
                )
            except Exception:
                logger.exception("Tool execution failed: %s", fn_name)
                result = {"error": f"Tool {fn_name} failed"}

            session = lecture_state.session
            if session:
                session.tool_calls_made += 1

            # Append tool result to history
            self._messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

        # One more model call so Groq can react to the tool results
        if quota_manager.can_make_call():
            try:
                text, _ = await self._call_model()
                quota_manager.record_call()
                session = lecture_state.session
                if session:
                    session.api_calls_used += 1
                if text:
                    await lecture_state.add_transcript_line(f"[AI] {text}")
            except Exception:
                logger.exception("GeminiOrchestrator: continuation call failed")

        return stop

    # ------------------------------------------------------------------
    # Context / helpers
    # ------------------------------------------------------------------

    def _build_context_message(self, events: list[ClassroomEvent]) -> str:
        """Build a classroom-state summary to inject each loop iteration."""
        if self._session_start:
            elapsed = (datetime.now(timezone.utc) - self._session_start).total_seconds()
            elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
        else:
            elapsed_str = "unknown"

        students = lecture_state.students
        present = [s for s in students.values() if s.is_present]
        distracted = [s for s in present if s.attention_score < config.DISTRACTION_THRESHOLD]
        avg_attention = (
            sum(s.attention_score for s in present) / len(present) if present else 1.0
        )

        lines = [
            f"[SYSTEM UPDATE — {elapsed_str} elapsed]",
            f"Students present: {len(present)}/{len(students)} | "
            f"Average attention: {avg_attention:.0%} | Distracted: {len(distracted)}",
            f"Current slide: {lecture_state.current_slide} | "
            f"Board elements: {len(lecture_state.board_elements)}",
            f"API quota remaining: {quota_manager.remaining()}",
        ]

        if distracted:
            lines.append(f"⚠ Distracted students: {', '.join(s.name for s in distracted)}")

        if events:
            lines.append(f"\nPending events ({len(events)}):")
            for ev in events:
                if ev.type == "student_speech":
                    lines.append(f"  • Student said: \"{ev.data.get('text', '')}\"")
                elif ev.type == "distraction":
                    student = students.get(ev.data.get("student_id", ""))
                    name = student.name if student else ev.data.get("student_id", "unknown")
                    lines.append(f"  • {name} has been distracted for {ev.data.get('duration', 0)}s")
                else:
                    lines.append(f"  • {ev.type}: {ev.data}")
        else:
            lines.append("\nNo pending events — continue the lecture.")

        return "\n".join(lines)

    async def _force_end(self) -> None:
        """Force-end the lecture when quota is exhausted."""
        await lecture_state.update_status("ended")
        await ws_hub.broadcast(
            create_event(
                EventType.LECTURE_ENDED,
                {
                    "reason": "quota_exhausted",
                    "api_calls_used": (
                        lecture_state.session.api_calls_used
                        if lecture_state.session else 0
                    ),
                },
            )
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
gemini_orchestrator = GeminiOrchestrator()

