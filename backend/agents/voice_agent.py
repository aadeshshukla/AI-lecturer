"""Voice agent — TTS output and STT input for the AI Autonomous Lecturer.

Two capabilities live in a single class:

* **Text-to-Speech (TTS):** Coqui TTS synthesises speech and ``sounddevice``
  plays it on the classroom speaker (system default or ``AUDIO_DEVICE_INDEX``).
* **Speech-to-Text (STT):** OpenAI Whisper transcribes speech captured by the
  laptop's built-in microphone (``MIC_DEVICE_INDEX``).  A lightweight energy-
  based Voice-Activity-Detection (VAD) loop runs in a background thread.

DEMO_MODE (``config.DEMO_MODE == True``):
  TTS is simulated with a short sleep; the real microphone is not opened.
  Call ``inject_mock_speech(text)`` to simulate a student question.
"""

import asyncio
import logging
import os
import tempfile
import threading
import time
from typing import Optional

from backend import config
from backend.models.event import ClassroomEvent
from backend.orchestrator.lecture_state import lecture_state
from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub

logger = logging.getLogger(__name__)

# VAD constants — energy threshold and silence duration are configurable via config.py
# so operators can tune them for different room acoustics without code changes.
_VAD_CHUNK_DURATION = 0.3   # seconds per audio chunk analysed for energy
_SAMPLE_RATE = 16_000        # Hz expected by Whisper


class VoiceAgent:
    """Manages text-to-speech output and speech-to-text input.

    Usage::

        agent = VoiceAgent()
        await agent.speak("Hello class!")
        agent.start_listening()
        # … lecture runs …
        agent.stop_listening()
    """

    def __init__(self) -> None:
        """Initialise TTS engine and prepare STT state."""
        self.is_speaking: bool = False
        self._stop_speaking_event = threading.Event()
        self._speak_thread: Optional[threading.Thread] = None

        self._listening: bool = False
        self._listen_thread: Optional[threading.Thread] = None

        # Whisper model (lazy-loaded on first start_listening call)
        self._whisper_model = None

        # TTS engine (lazy-loaded on first speak call)
        self._tts = None

        logger.info(
            "VoiceAgent initialised (DEMO_MODE=%s)", config.DEMO_MODE
        )

    # ------------------------------------------------------------------
    # TTS helpers
    # ------------------------------------------------------------------

    def _load_tts(self) -> None:
        """Lazy-load the Coqui TTS model on first use."""
        if self._tts is not None:
            return
        if config.DEMO_MODE:
            return
        try:
            from TTS.api import TTS as CoquiTTS  # type: ignore[import-untyped]

            logger.info("Loading Coqui TTS model: %s", config.TTS_MODEL)
            self._tts = CoquiTTS(model_name=config.TTS_MODEL)
            logger.info("Coqui TTS model loaded successfully")
        except Exception:
            logger.exception("Failed to load Coqui TTS model — falling back to demo mode")

    async def speak(self, text: str, emotion: str = "neutral") -> dict:
        """Synthesise *text* and play it on the classroom speaker.

        The method is async-friendly: TTS synthesis and audio playback run in a
        dedicated thread while the event loop stays free.

        Args:
            text: The text to speak out loud.
            emotion: Tone hint — "neutral" | "enthusiastic" | "serious" | "encouraging".
                     Currently logged only; Coqui TTS does not expose per-utterance
                     emotion control in the basic API.

        Returns:
            dict with keys ``status`` and ``duration_estimate`` (seconds).
        """
        logger.info("VoiceAgent.speak [%s]: %s", emotion, text[:120])
        self.is_speaking = True
        self._stop_speaking_event.clear()

        await ws_hub.broadcast(
            create_event(EventType.SPEAKING_START, {"text": text, "emotion": emotion})
        )
        await lecture_state.add_transcript_line(f"[AI] {text}")

        if config.DEMO_MODE or self._tts is None:
            self._load_tts()

        if config.DEMO_MODE or self._tts is None:
            # Simulate speaking: ~150 words per minute
            word_count = len(text.split())
            duration = max(0.5, word_count / 150 * 60)
            await asyncio.sleep(min(duration, 3.0))  # cap simulation at 3 s
            self.is_speaking = False
            await ws_hub.broadcast(
                create_event(EventType.SPEAKING_END, {"duration_ms": int(duration * 1000)})
            )
            return {"status": "speaking", "duration_estimate": duration}

        # Real TTS path — runs in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        duration_container: list[float] = [0.0]
        done_event = asyncio.Event()

        def _synth_and_play() -> None:
            tmp_path: str | None = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = tmp.name

                self._tts.tts_to_file(text=text, file_path=tmp_path)

                import soundfile as sf  # type: ignore[import-untyped]
                import sounddevice as sd  # type: ignore[import-untyped]

                data, samplerate = sf.read(tmp_path, dtype="float32")
                duration_container[0] = len(data) / samplerate

                device = (
                    config.AUDIO_DEVICE_INDEX
                    if config.AUDIO_DEVICE_INDEX != 0
                    else None
                )
                sd.play(data, samplerate, device=device)

                # Wait for playback or stop signal
                chunk = 0.1
                elapsed = 0.0
                while elapsed < duration_container[0]:
                    if self._stop_speaking_event.is_set():
                        sd.stop()
                        break
                    time.sleep(chunk)
                    elapsed += chunk

                sd.wait()
            except Exception:
                logger.exception("VoiceAgent: TTS playback error")
            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                self.is_speaking = False
                loop.call_soon_threadsafe(done_event.set)

        self._speak_thread = threading.Thread(
            target=_synth_and_play, daemon=True, name="tts-playback"
        )
        self._speak_thread.start()

        await done_event.wait()

        await ws_hub.broadcast(
            create_event(
                EventType.SPEAKING_END,
                {"duration_ms": int(duration_container[0] * 1000)},
            )
        )
        return {"status": "speaking", "duration_estimate": duration_container[0]}

    async def stop_speaking(self) -> dict:
        """Interrupt ongoing TTS playback immediately.

        Returns:
            dict with key ``status``.
        """
        logger.info("VoiceAgent.stop_speaking()")
        self._stop_speaking_event.set()
        self.is_speaking = False
        await ws_hub.broadcast(create_event(EventType.SPEAKING_END, {"duration_ms": 0}))
        return {"status": "stopped"}

    # ------------------------------------------------------------------
    # STT helpers
    # ------------------------------------------------------------------

    def _load_whisper(self) -> None:
        """Lazy-load the Whisper model."""
        if self._whisper_model is not None:
            return
        try:
            import whisper  # type: ignore[import-untyped]

            logger.info("Loading Whisper model: %s", config.STT_MODEL)
            self._whisper_model = whisper.load_model(config.STT_MODEL)
            logger.info("Whisper model loaded successfully")
        except Exception:
            logger.exception("Failed to load Whisper model")

    def start_listening(self) -> None:
        """Start the background microphone capture + transcription loop.

        In DEMO_MODE this is a no-op; use ``inject_mock_speech`` instead.
        """
        if config.DEMO_MODE:
            logger.info("VoiceAgent.start_listening: DEMO_MODE — no real mic")
            return
        if self._listening:
            logger.warning("VoiceAgent.start_listening: already listening")
            return

        self._load_whisper()
        self._listening = True
        self._listen_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="stt-listen"
        )
        self._listen_thread.start()
        logger.info("VoiceAgent: started listening on mic device=%d", config.MIC_DEVICE_INDEX)

    def stop_listening(self) -> None:
        """Signal the background listening thread to stop."""
        self._listening = False
        logger.info("VoiceAgent.stop_listening: signalled")

    def _listen_loop(self) -> None:
        """Background thread: continuous VAD → record → transcribe loop."""
        try:
            import pyaudio  # type: ignore[import-untyped]
            import numpy as np  # type: ignore[import-untyped]
            import whisper  # type: ignore[import-untyped]
            import wave
        except ImportError:
            logger.exception("VoiceAgent: required library not installed (pyaudio/numpy)")
            return

        pa = pyaudio.PyAudio()
        chunk_samples = int(_SAMPLE_RATE * _VAD_CHUNK_DURATION)

        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=_SAMPLE_RATE,
                input=True,
                input_device_index=(
                    config.MIC_DEVICE_INDEX if config.MIC_DEVICE_INDEX != 0 else None
                ),
                frames_per_buffer=chunk_samples,
            )
        except Exception:
            logger.exception("VoiceAgent: cannot open microphone stream")
            pa.terminate()
            return

        logger.info("VoiceAgent: microphone stream opened")
        recording: list[bytes] = []
        silence_chunks = 0
        # Use configurable VAD parameters from config.py
        vad_energy_threshold = config.VAD_ENERGY_THRESHOLD
        vad_silence_duration = config.VAD_SILENCE_DURATION
        max_silence_chunks = int(vad_silence_duration / _VAD_CHUNK_DURATION)
        in_speech = False

        while self._listening:
            # Mute while TTS is playing to avoid echo
            if self.is_speaking:
                time.sleep(_VAD_CHUNK_DURATION)
                continue

            try:
                raw = stream.read(chunk_samples, exception_on_overflow=False)
            except Exception:
                logger.exception("VoiceAgent: microphone read error")
                break

            # Compute RMS energy for VAD
            import array as _array
            samples = _array.array("h", raw)
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5

            if rms > vad_energy_threshold:
                if not in_speech:
                    logger.debug("VoiceAgent: speech detected (rms=%.0f)", rms)
                    in_speech = True
                    recording = []
                    silence_chunks = 0
                recording.append(raw)
            elif in_speech:
                recording.append(raw)
                silence_chunks += 1
                if silence_chunks >= max_silence_chunks:
                    # End of utterance — transcribe
                    in_speech = False
                    self._transcribe_and_emit(recording, pa, wave)
                    recording = []
                    silence_chunks = 0

        stream.stop_stream()
        stream.close()
        pa.terminate()
        logger.info("VoiceAgent: microphone stream closed")

    def _transcribe_and_emit(
        self,
        frames: list[bytes],
        pa,  # noqa: ANN001
        wave,  # noqa: ANN001
    ) -> None:
        """Write recorded frames to a temp file and transcribe with Whisper.

        Emits a ``STUDENT_SPEECH`` WebSocket event and enqueues a
        ``ClassroomEvent`` so Gemini can react.

        Args:
            frames: List of raw PCM byte chunks captured during the utterance.
            pa: The ``pyaudio.PyAudio`` instance (used to query sample width).
            wave: The ``wave`` standard-library module.
        """
        if self._whisper_model is None:
            logger.warning("VoiceAgent: Whisper model not loaded — skipping transcription")
            return

        tmp_path: str | None = None
        try:
            import pyaudio  # type: ignore[import-untyped]

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
                wf.setframerate(_SAMPLE_RATE)
                wf.writeframes(b"".join(frames))

            result = self._whisper_model.transcribe(tmp_path)
            transcript: str = result.get("text", "").strip()
            logger.info("VoiceAgent: transcribed: %r", transcript)

            if not transcript:
                return

            # Schedule async work from this thread
            try:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(
                    loop.create_task,
                    self._emit_speech_event(transcript),
                )
            except RuntimeError:
                logger.warning("VoiceAgent: no event loop — speech event not emitted")

        except Exception:
            logger.exception("VoiceAgent: transcription error")
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    async def _emit_speech_event(self, transcript: str) -> None:
        """Enqueue a classroom event and broadcast a WebSocket event.

        Args:
            transcript: The transcribed student speech text.
        """
        event = ClassroomEvent(
            type="student_speech",
            data={"text": transcript, "source": "microphone"},
        )
        await lecture_state.add_event(event)
        await ws_hub.broadcast(
            create_event(EventType.STUDENT_SPEECH, {"transcript": transcript})
        )

    # ------------------------------------------------------------------
    # Demo helpers
    # ------------------------------------------------------------------

    def inject_mock_speech(self, text: str) -> None:
        """Simulate a student asking a question (DEMO_MODE only).

        Schedules an async emission of a student_speech event on the
        running event loop.

        Args:
            text: The mock student speech to inject.
        """
        logger.info("VoiceAgent.inject_mock_speech: %r", text)
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._emit_speech_event(text))
        except RuntimeError:
            logger.warning("VoiceAgent: no event loop for inject_mock_speech")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
voice_agent = VoiceAgent()
