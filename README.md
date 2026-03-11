# 🎓 AI Autonomous Lecturer

> A zero-budget autonomous AI lecturer system powered by Google Gemini 2.5 Flash

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Node 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

---

## ✨ Features

- **Autonomous lecture delivery** via Google Gemini 2.5 Flash (free tier — 250 req/day)
- **Real-time virtual whiteboard** powered by react-konva
- **Voice synthesis** (Coqui TTS) and **speech recognition** (OpenAI Whisper)
- **Computer vision student monitoring** (YOLOv8 person detection + DeepFace recognition)
- **RAG knowledge base** (ChromaDB + sentence-transformers for lecture material)
- **Live attendance tracking** via face recognition
- **Student attention monitoring** with automated warnings
- **Demo mode** for hardware-free expo/presentation demonstrations

---

## 🏗️ Architecture

| Layer | Technology |
|-------|-----------|
| **Backend** | Python FastAPI + WebSocket event bus |
| **Frontend** | React 18 + Vite + TailwindCSS |
| **AI Brain** | Google Gemini 2.5 Flash (function calling) |
| **Speech** | Whisper STT (local) + Coqui TTS (local) |
| **Vision** | YOLOv8 (detection) + DeepFace (face recognition) |
| **Knowledge** | ChromaDB vector DB + sentence-transformers |
| **Storage** | SQLite (students/sessions) + ChromaDB (embeddings) |

**Event flow:**
```
Camera/Mic → Agents → ClassroomEvent queue → Gemini Orchestrator
              ↓                                      ↓
         WebSocket hub ←────────── Tool calls (speak, write, warn, …)
              ↓
         React Frontend (Dashboard / Projector / StudentView)
```

---

## 📋 Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Free Google Gemini API key** — get one at https://aistudio.google.com/app/apikey

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/aadeshshukla/AI-lecturer.git
cd AI-lecturer
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd frontend && npm install && cd ..
```

### 4. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set your Gemini API key:

```
GOOGLE_API_KEY=your_free_gemini_api_key_here
```

### 5. Start the backend

```bash
python -m uvicorn backend.main:app --port 8000
```

### 6. Start the frontend

```bash
cd frontend && npm run dev
```

### 7. Open the app

| View | URL | Purpose |
|------|-----|---------|
| **Dashboard** | http://localhost:5173 | Instructor control panel |
| **Projector** | http://localhost:5173/projector | Classroom/HDMI display (fullscreen) |
| **Student View** | http://localhost:5173/student | Per-student attention display |

---

## 🧪 Demo Mode (No Hardware Required)

Set `DEMO_MODE=true` in your `.env` file:

```
DEMO_MODE=true
```

In demo mode:

- **Mock camera** generates synthetic student attention scores — no webcam needed
- **Mock microphone** injects pre-scripted student questions every 30–60 seconds — no real mic needed
- **5 demo students** are auto-seeded on startup (Alice Chen, Bob Kumar, Carol Smith, David Park, Eve Johnson)
- TTS still broadcasts `speaking_start`/`speaking_end` WebSocket events (UI updates) but skips actual audio playback

Perfect for expo and presentation demos on machines without camera/microphone hardware.

---

## 🎥 Hardware Showcase Profile (Mobile Camera + Bluetooth Speaker + Projector)

Use this profile when you have:
- Mobile phone camera (DroidCam/IP Webcam)
- Bluetooth speaker
- Projector/second display
- No microphone available

Set these in `.env`:

```env
DEMO_MODE=false
ENABLE_MIC=false
CAMERA_INDEX=http://<your-phone-ip>:4747/video
GEMINI_LOOP_INTERVAL_SECONDS=3.0
```

Notes:
- Set your Bluetooth speaker as the **system default output device** before starting the backend.
- Open `http://localhost:5173/projector` on the projector display and press `F11`.
- For a stable showcase, start a **15 minute** lecture from Dashboard (Duration = 15).
- If YOLO/Torch fails on Windows, the backend now auto-falls back to lightweight camera mode so the lecture can continue.

---

## 🔧 Hardware Setup (Real Classroom Use)

### Speaker
Coqui TTS routes audio through the **system default audio output**. Set `AUDIO_DEVICE_INDEX` in `.env` if you need a specific device (e.g., Bluetooth speaker):

```bash
# List available audio devices
python -c "import sounddevice; print(sounddevice.query_devices())"
```

### Microphone
The system uses the **laptop built-in microphone** by default. Adjust `MIC_DEVICE_INDEX` if needed. Voice Activity Detection (VAD) settings:

```
VAD_ENERGY_THRESHOLD=500.0   # raise for noisy rooms
VAD_SILENCE_DURATION=1.5     # seconds of silence before an utterance ends
```

### Camera
Two options:

**Option A — Phone camera via DroidCam / IP Webcam app (recommended for demos)**
1. Install [DroidCam](https://www.dev47apps.com/) on your Android phone
2. Note the IP address shown in the app (e.g., `http://192.168.1.5:4747`)
3. Set in `.env`: `CAMERA_INDEX=http://192.168.1.5:4747/video`

**Option B — USB webcam**
```
CAMERA_INDEX=0   # or 1, 2 for additional cameras
```

### Projector
1. Connect via HDMI
2. Open http://localhost:5173/projector in a browser on the **second display**
3. Press **F11** for fullscreen

---

## 📁 Project Structure

```
AI-lecturer/
├── README.md
├── LICENSE
├── DEMO_CHECKLIST.md
├── .env.example
├── requirements.txt
├── AI_LECTURER_SPEC.md
│
├── backend/
│   ├── main.py                   # FastAPI entry point + all routes
│   ├── config.py                 # Configuration constants (from .env)
│   │
│   ├── orchestrator/
│   │   ├── gemini_agent.py       # Gemini 2.5 Flash autonomous loop
│   │   ├── system_prompt.py      # Professor persona & instructions
│   │   ├── lecture_state.py      # Shared in-memory state
│   │   └── quota_manager.py      # Daily API quota tracker
│   │
│   ├── agents/
│   │   ├── voice_agent.py        # TTS output + STT input (Whisper)
│   │   ├── vision_agent.py       # Camera monitoring (YOLOv8 + DeepFace)
│   │   ├── knowledge_agent.py    # RAG retrieval (ChromaDB)
│   │   └── attention_agent.py    # Attention classification (DistilBERT)
│   │
│   ├── demo/
│   │   ├── mock_camera.py        # Synthetic student detections (DEMO_MODE)
│   │   ├── mock_microphone.py    # Scripted question injection (DEMO_MODE)
│   │   └── mock_students.py      # Auto-seed 5 demo students (DEMO_MODE)
│   │
│   ├── mcp_server/
│   │   ├── server.py             # Tool registry + execution engine
│   │   └── tools/                # speak, board, slide, classroom, knowledge, control
│   │
│   ├── database/
│   │   ├── db.py                 # SQLAlchemy setup + ORM models
│   │   ├── students.py           # Student CRUD operations
│   │   └── sessions.py           # Lecture session CRUD
│   │
│   ├── models/
│   │   ├── student.py            # Student dataclass
│   │   ├── lecture.py            # LectureSession dataclass
│   │   └── event.py              # ClassroomEvent dataclass
│   │
│   └── websocket/
│       ├── hub.py                # WebSocket connection manager
│       └── events.py             # Event type constants + factory
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.jsx     # Instructor control panel
│       │   ├── Projector.jsx     # Fullscreen classroom display
│       │   └── StudentView.jsx   # Per-student attention view
│       ├── components/
│       │   ├── VirtualBoard.jsx  # react-konva whiteboard
│       │   ├── SlideViewer.jsx   # Slide display
│       │   ├── AttendanceGrid.jsx
│       │   ├── TranscriptFeed.jsx
│       │   ├── LectureControls.jsx
│       │   ├── StatusBar.jsx
│       │   └── AlertBanner.jsx
│       └── hooks/
│           ├── useWebSocket.js   # WebSocket connection + events
│           ├── useLectureState.js
│           └── useStudents.js
│
└── data/
    ├── knowledge_base/           # Upload lecture PDFs here
    ├── student_photos/           # Student registration photos
    └── lectures/                 # Session recordings (future)
```

---

## 🛠️ Configuration

All settings live in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | — | **Required.** Free Gemini API key from https://aistudio.google.com/app/apikey |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `GEMINI_LOOP_INTERVAL_SECONDS` | `2.0` | Sleep between autonomous loop iterations (conserves quota) |
| `BACKEND_PORT` | `8000` | FastAPI server port |
| `FRONTEND_PORT` | `5173` | Vite dev server port |
| `WEBSOCKET_URL` | `ws://localhost:8000/ws` | WebSocket URL for the frontend |
| `CAMERA_INDEX` | `0` | Camera source: int for USB, URL for IP camera |
| `CAMERA_FPS` | `10` | Frames per second for the vision loop |
| `ATTENTION_CHECK_INTERVAL` | `5` | Seconds between attention score updates |
| `TTS_MODEL` | `tts_models/en/ljspeech/tacotron2-DDC` | Coqui TTS model |
| `STT_MODEL` | `base` | Whisper model size (`tiny`, `base`, `small`, `medium`) |
| `AUDIO_DEVICE_INDEX` | `0` | Speaker device index |
| `MIC_DEVICE_INDEX` | `0` | Microphone device index |
| `VAD_ENERGY_THRESHOLD` | `500.0` | RMS energy threshold for voice activity detection |
| `VAD_SILENCE_DURATION` | `1.5` | Seconds of silence to end an utterance |
| `YOLO_MODEL` | `yolov8n.pt` | YOLOv8 model variant |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model for RAG |
| `DISTRACTION_THRESHOLD` | `0.3` | Attention score below which a student is distracted |
| `DATABASE_URL` | `sqlite:///./data/lecturer.db` | SQLAlchemy database URL |
| `CHROMA_PATH` | `./data/chroma_db` | ChromaDB persistence directory |
| `MAX_LECTURE_DURATION` | `3600` | Maximum lecture length in seconds |
| `LECTURE_LANGUAGE` | `en` | Lecture language code |
| `DEFAULT_DIFFICULTY` | `intermediate` | Default lecture difficulty |
| `DEMO_MODE` | `false` | Set to `true` for expo demos without real hardware |

---

## 🎬 How a Lecture Works

1. **Instructor opens Dashboard** → clicks "Start Lecture" → enters topic + duration
2. **Backend initialises agents:**
   - `VisionAgent` opens camera (or mock camera in DEMO_MODE) and starts monitoring
   - `VoiceAgent` starts listening on the microphone (or mock mic in DEMO_MODE)
   - `KnowledgeAgent` initialises ChromaDB for RAG retrieval
3. **Gemini autonomous loop starts** — every `GEMINI_LOOP_INTERVAL_SECONDS`:
   - Reads current `lecture_state` (slides, transcript, student attention, events)
   - Sends context to Gemini 2.5 Flash with the professor system prompt
   - Gemini decides the next action and calls the appropriate tool
4. **Tool calls are executed:**
   - `speak(text)` → Coqui TTS synthesises audio → plays on speaker → WebSocket event
   - `writeOnBoard(content)` → updates virtual whiteboard → Projector display updates
   - `advanceSlide()` → increments slide counter → frontend updates
   - `warnStudent(id)` → increments warning counter → Dashboard alerts
   - `scanAttendance()` → DeepFace identifies faces → marks students present/absent
5. **Student events feed back into the loop:**
   - `VisionAgent` emits `student_distracted` events when attention drops
   - `VoiceAgent` transcribes student questions and emits `student_speech` events
   - Gemini reacts to these events in the next loop iteration
6. **Lecture ends** when Gemini calls `endLecture()` or the instructor clicks "End"

---

## 💰 Cost: ₹0

Every technology used is either open-source or on a free tier:

| Component | Cost | Notes |
|-----------|------|-------|
| Gemini 2.5 Flash API | ₹0 | Free tier: **250 requests/day** |
| Whisper STT | ₹0 | Runs locally |
| Coqui TTS | ₹0 | Runs locally |
| YOLOv8 | ₹0 | Runs locally |
| DeepFace | ₹0 | Runs locally |
| DistilBERT | ₹0 | Runs locally |
| ChromaDB + LlamaIndex | ₹0 | Runs locally |
| FastAPI + SQLite | ₹0 | Open source |
| React + Vite + Tailwind | ₹0 | Open source |
| **TOTAL** | **₹0** | |

**Free tier math:** One 45-minute lecture ≈ 50–80 Gemini tool calls.  
250 req/day ÷ 80 calls/lecture = **3–5 full demos per day**.

---

## 📋 Expo Demo Checklist

See [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md) for the full printable checklist.

**Quick summary:**
- [ ] Valid `GOOGLE_API_KEY` in `.env`
- [ ] Backend and frontend servers running
- [ ] Dashboard open on laptop, Projector URL open on HDMI display (fullscreen)
- [ ] Demo topic chosen and materials uploaded to `data/knowledge_base/`
- [ ] Demo flow practiced at least twice

---

## 🔄 Fallback Plans

### Option A — Gemini 2.5 Flash-Lite (1,000 req/day free, more headroom)
```bash
# In .env:
GEMINI_MODEL=gemini-2.5-flash-lite
```

### Option B — Local Ollama + Llama 3 (unlimited, requires a decent GPU)
```bash
brew install ollama
ollama pull llama3:8b
# Update backend/orchestrator/gemini_agent.py to use the OpenAI-compatible client:
# base_url="http://localhost:11434/v1", api_key="ollama"
```

### Option C — OpenAI ($5 free credits for new accounts)
```python
# pip install openai
from openai import OpenAI
client = OpenAI(api_key="your_key")
# Use model="gpt-4o-mini" for cheapest option
```

---

## 📜 License

[MIT](LICENSE) © 2026 aadeshshukla
