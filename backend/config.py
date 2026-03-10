"""Configuration constants for the AI Autonomous Lecturer System.

All values are loaded from environment variables via python-dotenv.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Google Gemini (brain — FREE tier: 250 requests/day)
# ---------------------------------------------------------------------------
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "5173"))
WEBSOCKET_URL: str = os.getenv("WEBSOCKET_URL", "ws://localhost:8000/ws")

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", "0"))
CAMERA_FPS: int = int(os.getenv("CAMERA_FPS", "10"))
ATTENTION_CHECK_INTERVAL: int = int(os.getenv("ATTENTION_CHECK_INTERVAL", "5"))

# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
TTS_MODEL: str = os.getenv("TTS_MODEL", "tts_models/en/ljspeech/tacotron2-DDC")
STT_MODEL: str = os.getenv("STT_MODEL", "base")
AUDIO_DEVICE_INDEX: int = int(os.getenv("AUDIO_DEVICE_INDEX", "0"))
MIC_DEVICE_INDEX: int = int(os.getenv("MIC_DEVICE_INDEX", "0"))

# ---------------------------------------------------------------------------
# AI Models
# ---------------------------------------------------------------------------
YOLO_MODEL: str = os.getenv("YOLO_MODEL", "yolov8n.pt")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/lecturer.db")
CHROMA_PATH: str = os.getenv("CHROMA_PATH", "./data/chroma_db")

# ---------------------------------------------------------------------------
# Lecture settings
# ---------------------------------------------------------------------------
MAX_LECTURE_DURATION: int = int(os.getenv("MAX_LECTURE_DURATION", "3600"))
LECTURE_LANGUAGE: str = os.getenv("LECTURE_LANGUAGE", "en")
DEFAULT_DIFFICULTY: str = os.getenv("DEFAULT_DIFFICULTY", "intermediate")

# ---------------------------------------------------------------------------
# Demo mode (no real hardware required)
# ---------------------------------------------------------------------------
DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"
