"""Voice agent placeholder (TTS output + STT input).

TODO PR2: Implement:
  - Coqui TTS text-to-speech using sounddevice for playback.
  - OpenAI Whisper speech-to-text for student microphone input.
  - Voice activity detection (VAD) to avoid continuous transcription.
  - Mute STT while TTS is playing (avoid echo).
  - Emit WebSocket events: speaking_start, speaking_end, student_speech.
"""
