# AI Autonomous Lecturer 🎓

A **lightweight, demo-friendly AI lecturer** that runs autonomously — no GPU, no PyTorch, no heavy downloads.

The AI delivers a full lecture, speaks out loud through your browser, writes on a virtual whiteboard, advances slides, and responds to student questions — all powered by **Groq's free-tier API** (Llama 3).

## Architecture

```
Browser (Frontend)          FastAPI Backend         Groq API
────────────────────        ───────────────         ─────────
• Projector view            • WebSocket hub    ←→   Llama 3.1 8B
• Virtual whiteboard        • Lecture routes
• TTS (Web Speech API)      • In-memory state
• STT (Web Speech API)
• Camera (getUserMedia)
```

The Python backend is a thin relay: **FastAPI + Groq + WebSockets**. All heavy processing (speech, camera) runs in the browser.

## Prerequisites

- **Python 3.11+**
- **Groq API key** — free at [https://console.groq.com](https://console.groq.com)

## Setup

```bash
# 1. Install dependencies (4 packages — no GPU, no PyTorch)
pip install -r requirements.txt

# 2. Configure your API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 3. Run
python -m uvicorn backend.main:app --port 8000
```

## Usage

| View | URL | Purpose |
|------|-----|---------|
| Teacher Dashboard | `http://localhost:8000` | Start/stop lectures, view transcript, manage students |
| Projector View | `http://localhost:8000/projector` | Full-screen display for projector — open on second screen |

### Starting a Lecture
1. Open `http://localhost:8000` in your browser
2. Enter a topic (e.g. "Introduction to Machine Learning")
3. Set duration and difficulty
4. Click **▶ Start Lecture**
5. Open `http://localhost:8000/projector` on your projector/second screen

### Phone Camera Setup
Connect your phone to the same Wi-Fi as your laptop, then use one of:
- **DroidCam** (Android/iOS) — enter `http://<phone-ip>:4747/video` as camera URL
- **IP Webcam** (Android) — enter the stream URL shown in the app

### Student Questions
Click **🎤 Ask a Question (STT)** on the dashboard to speak a question using your browser's speech recognition. The AI will hear it and respond.

### Bluetooth Speaker
The AI speaks through the browser's built-in **Web Speech Synthesis API**. Connect a Bluetooth speaker to the laptop running the projector view — it will automatically play through it.

## How It Works

1. You start a lecture with a topic and duration
2. The Groq/Llama AI enters an autonomous loop:
   - Calls `speak()` → browser plays TTS via Web Speech API
   - Calls `write_on_board()` → whiteboard updates in projector view
   - Calls `advance_slide()` / `generate_slide()` → slide panel updates
   - Calls `ask_class()` → question displayed for students
3. Student speech captured via STT is sent to the AI as an event
4. AI responds and continues the lecture

## Demo Setup (Expo/Classroom)

```
Laptop:  python -m uvicorn backend.main:app --port 8000
         Browser tab 1: http://localhost:8000        ← Teacher controls
         Browser tab 2: http://localhost:8000/projector ← Connect to projector

Phone:   DroidCam or IP Webcam app (optional camera feed)
Speaker: Bluetooth connected to laptop (plays AI voice)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Model name (faster/cheaper) or `llama-3.3-70b-versatile` |
| `BACKEND_PORT` | `8000` | Server port |
| `GEMINI_LOOP_INTERVAL_SECONDS` | `3.0` | Seconds between AI loop iterations |

## License

MIT
