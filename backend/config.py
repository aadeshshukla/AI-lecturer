"""Configuration constants for the AI Autonomous Lecturer System.

All values are loaded from environment variables via python-dotenv.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Groq (free tier: 14,400 req/day — sign up at https://console.groq.com)
# ---------------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "5173"))
WEBSOCKET_URL: str = os.getenv("WEBSOCKET_URL", "ws://localhost:8000/ws")

# ---------------------------------------------------------------------------
# Lecture settings
# ---------------------------------------------------------------------------
# Seconds to sleep between autonomous-loop iterations.
GEMINI_LOOP_INTERVAL_SECONDS: float = float(os.getenv("GEMINI_LOOP_INTERVAL_SECONDS", "3.0"))
MAX_LECTURE_DURATION: int = int(os.getenv("MAX_LECTURE_DURATION", "3600"))
LECTURE_LANGUAGE: str = os.getenv("LECTURE_LANGUAGE", "en")
DEFAULT_DIFFICULTY: str = os.getenv("DEFAULT_DIFFICULTY", "intermediate")
