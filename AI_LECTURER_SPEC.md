# AI AUTONOMOUS LECTURER SYSTEM
## Complete Project Specification for AI-Assisted Code Generation
> Feed this document to GitHub Copilot to generate the full codebase.

---

## PROJECT OVERVIEW

**Goal:** Build an autonomous AI lecturer that can independently deliver lectures to a real classroom. It controls speakers, projector, virtual whiteboard, monitors students via camera, handles Q&A via microphone, and manages classroom behavior — all without human intervention.

**Core Philosophy:** Gemini 2.5 Flash is the brain. It reasons, decides, and acts. Every physical output (speech, board writing, slide changes, student warnings) is executed by calling function tools. Gemini runs in a continuous autonomous loop until the lecture ends.

**Budget:** ₹0 — Every single technology used in this project is either open-source or available on a free tier. No paid APIs, no subscriptions.

---

## TECH STACK

### Primary AI
- **Orchestrator:** Google Gemini 2.5 Flash via Google AI Studio API (FREE tier — 250 requests/day)
- **Protocol:** Gemini Function Calling — Gemini calls tools to control everything
- **API Key:** Free from https://aistudio.google.com/app/apikey

### Open Source AI Models (All run locally — ₹0)
| Model | Purpose | Library | License |
|-------|---------|---------|---------|
| Whisper (openai/whisper) | Speech-to-text (mic input) | openai-whisper | MIT |
| Coqui TTS (tts) | Text-to-speech (speaker output) | TTS (pip) | MPL-2.0 |
| YOLOv8 (ultralytics) | Real-time face/person detection | ultralytics | AGPL-3.0 |
| DeepFace / FaceNet | Student face recognition & attendance | deepface | MIT |
| BERT (distilbert) | Sentiment/attention classification | transformers | Apache 2.0 |
| LlamaIndex | RAG over lecture knowledge base | llama-index | MIT |

### Infrastructure (All free & open-source)
| Component | Technology | License |
|-----------|-----------|---------|
| Backend Server | Python FastAPI | MIT |
| Event Bus | WebSocket (FastAPI WebSockets) | MIT |
| Vector DB | ChromaDB (local, no cloud needed) | Apache 2.0 |
| Session DB | SQLite (student records, attendance) | Public Domain |
| Frontend Dashboard | React + Vite | MIT |
| Virtual Board | React + Konva.js (canvas) | MIT |
| Slides | reveal.js (auto-generated HTML) | MIT |
| Projector Output | Browser fullscreen / OBS virtual cam | Free |

### Language
- **Backend:** Python 3.11+
- **Frontend:** React 18 + Vite + TailwindCSS

---

## COST BREAKDOWN (Proving ₹0)

| Component | Cost | Notes |
|-----------|------|-------|
| Gemini 2.5 Flash API | ₹0 | Free tier: 250 req/day → enough for 3-5 demos/day |
| Whisper STT | ₹0 | Runs locally |
| Coqui TTS | ₹0 | Runs locally |
| YOLOv8 | ₹0 | Runs locally |
| DeepFace | ₹0 | Runs locally |
| BERT/DistilBERT | ₹0 | Runs locally |
| LlamaIndex + ChromaDB | ₹0 | Runs locally |
| FastAPI + SQLite | ₹0 | Open source |
| React + Vite | ₹0 | Open source |
| **TOTAL** | **₹0** | |

**Free tier math:** One 45-min demo ≈ 50-80 tool calls. Gemini free tier = 250 req/day. That's 3-5 full demos per day, more than enough for 5-6 total demos.

---

## PROJECT DIRECTORY STRUCTURE

```
ai-lecturer/
├── README.md
├── .env                          # API keys and config
├── requirements.txt              # Python dependencies
├── package.json                  # Root workspace
│
├── backend/
│   ├── main.py                   # Entry point — starts all services
│   ├── config.py                 # All configuration constants
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── gemini_agent.py       # Gemini 2.5 Flash autonomous loop
│   │   ├── system_prompt.py      # Gemini's professor persona & instructions
│   │   └── lecture_state.py      # Shared state across all agents
│   │
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   ├── server.py             # Tool registry and execution engine
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── speech_tools.py   # speak(), stop_speaking()
│   │   │   ├── board_tools.py    # writeOnBoard(), clearBoard(), drawDiagram()
│   │   │   ├── slide_tools.py    # advanceSlide(), goToSlide(), showSlide()
│   │   │   ├── classroom_tools.py # warnStudent(), callOnStudent(), scanAttendance()
│   │   │   ├── knowledge_tools.py # queryKnowledge(), addToMemory()
│   │   │   └── control_tools.py  # pauseLecture(), endLecture(), setLectureMode()
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── voice_agent.py        # TTS output + STT input (Whisper + Coqui)
│   │   ├── vision_agent.py       # Camera processing (YOLO + DeepFace)
│   │   ├── attention_agent.py    # Student attention monitoring (BERT)
│   │   └── knowledge_agent.py    # RAG knowledge retrieval (LlamaIndex + Chroma)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── student.py            # Student dataclass
│   │   ├── lecture.py            # Lecture session dataclass
│   │   └── event.py              # Classroom event dataclass
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py                 # SQLite connection + migrations
│   │   ├── students.py           # Student CRUD operations
│   │   └── sessions.py           # Lecture session logging
│   │
│   └── websocket/
│       ├── __init__.py
│       ├── hub.py                # WebSocket broadcast hub
│       └── events.py             # Event type definitions
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx               # Root app + routing
│       ├── main.jsx
│       │
│       ├── pages/
│       │   ├── Dashboard.jsx     # Instructor control panel
│       │   ├── Projector.jsx     # Fullscreen projector view (shown on projector)
│       │   └── StudentView.jsx   # Student-facing alert/Q&A view
│       │
│       ├── components/
│       │   ├── VirtualBoard.jsx  # Konva.js whiteboard (Gemini writes here)
│       │   ├── SlideViewer.jsx   # reveal.js slide renderer
│       │   ├── AttendanceGrid.jsx # Live student attendance grid
│       │   ├── AlertBanner.jsx   # Student warning display
│       │   ├── TranscriptFeed.jsx # Live lecture transcript
│       │   ├── StatusBar.jsx     # AI lecturer status indicator
│       │   └── LectureControls.jsx # Start/stop/pause buttons
│       │
│       └── hooks/
│           ├── useWebSocket.js   # WebSocket connection hook
│           ├── useLectureState.js # Lecture state management
│           └── useStudents.js    # Student data hook
│
└── data/
    ├── knowledge_base/           # Drop lecture PDFs/docs here for RAG
    ├── student_photos/           # Student face photos for recognition
    └── lectures/                 # Generated lecture sessions stored here
```

---

## ENVIRONMENT VARIABLES (.env)

```env
# Google Gemini (FREE — get key from https://aistudio.google.com/app/apikey)
GOOGLE_API_KEY=your_free_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Server
BACKEND_PORT=8000
FRONTEND_PORT=5173
WEBSOCKET_URL=ws://localhost:8000/ws

# Camera
CAMERA_INDEX=0                    # 0 = default webcam
CAMERA_FPS=10                     # Frames per second for processing
ATTENTION_CHECK_INTERVAL=5        # Seconds between attention scans

# Audio
TTS_MODEL=tts_models/en/ljspeech/tacotron2-DDC   # Coqui TTS model
STT_MODEL=base                    # Whisper model size: tiny/base/small/medium
AUDIO_DEVICE_INDEX=0              # Speaker output device
MIC_DEVICE_INDEX=0               # Microphone input device

# AI Models  
YOLO_MODEL=yolov8n.pt            # YOLOv8 nano for speed
EMBEDDING_MODEL=all-MiniLM-L6-v2 # Sentence transformer for RAG

# Database
DATABASE_URL=sqlite:///./data/lecturer.db
CHROMA_PATH=./data/chroma_db

# Lecture Settings
MAX_LECTURE_DURATION=3600         # Max seconds (1 hour)
LECTURE_LANGUAGE=en
DEFAULT_DIFFICULTY=intermediate   # beginner / intermediate / advanced

# Demo Mode (set to true to use mock camera/mic — no real hardware needed)
DEMO_MODE=false
```

---

## CORE MODULE SPECIFICATIONS

---

### 1. TOOL REGISTRY (`backend/mcp_server/server.py`)

**Purpose:** Exposes all classroom control actions as function tools. Gemini calls these autonomously via function calling.

```python
# IMPLEMENT THIS MODULE
# Requirements:
# - Define all tools as Gemini function declarations (JSON schema)
# - Each tool maps to a Python async function
# - Each tool must broadcast a WebSocket event after execution
# - Tools must be async
# - Tool calls must be logged to database

# TOOLS TO REGISTER (as Gemini function_declarations):
tools = [
    "speak",           # Convert text to speech via TTS, play on speakers
    "stop_speaking",   # Interrupt current TTS playback
    "write_on_board",  # Write text/equation on virtual whiteboard
    "draw_diagram",    # Draw a named diagram type (flowchart, mindmap, etc.)
    "clear_board",     # Clear the whiteboard
    "highlight_board", # Highlight a region on the board
    "advance_slide",   # Go to next slide
    "go_to_slide",     # Jump to specific slide number
    "generate_slide",  # Generate a new slide on the fly from text
    "warn_student",    # Issue warning to student by ID with reason
    "call_on_student", # Ask student a question (triggers alert on their device)
    "scan_attendance", # Run face recognition on camera feed
    "query_knowledge", # RAG query against knowledge base
    "get_class_status",# Returns: who is distracted, attendance, time elapsed
    "pause_lecture",   # Pause everything
    "end_lecture",     # Gracefully end the session
    "set_difficulty",  # Change lecture complexity level
    "ask_class",       # Ask a question to the whole class, wait for hands
]

# GEMINI FUNCTION DECLARATION FORMAT:
function_declarations = [
    {
        "name": "speak",
        "description": "Convert text to speech and play on classroom speakers",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to speak out loud"},
                "emotion": {"type": "string", "enum": ["neutral", "enthusiastic", "serious", "encouraging"], "description": "Tone of voice"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "write_on_board",
        "description": "Write text or equation on the virtual whiteboard",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Text or LaTeX equation to write"},
                "position": {"type": "string", "description": "Position: 'auto' or '{x,y}' coordinates"},
                "style": {"type": "string", "enum": ["normal", "formula", "heading", "example"], "description": "Visual style"}
            },
            "required": ["content"]
        }
    },
    # ... define all 18 tools in this format
]
```

**Tool Input/Output Schemas:**

```python
# speak(text: str, emotion: str = "neutral") -> {"status": "speaking", "duration_estimate": float}
# write_on_board(content: str, position: str = "auto", style: str = "normal") -> {"status": "written", "element_id": str}
# draw_diagram(diagram_type: str, data: dict) -> {"status": "drawn", "element_id": str}
#   diagram_type options: "flowchart", "mindmap", "timeline", "graph", "table", "formula"
# warn_student(student_id: str, reason: str, severity: str = "mild") -> {"status": "warned", "student_name": str}
#   severity options: "mild", "moderate", "severe"
# scan_attendance() -> {"present": [student_id], "absent": [student_id], "unknown": int}
# query_knowledge(query: str, top_k: int = 3) -> {"results": [{"text": str, "source": str}]}
# get_class_status() -> {"distracted_students": [...], "attentive_count": int, "time_elapsed": int, "questions_pending": int}
```

---

### 2. GEMINI ORCHESTRATOR (`backend/orchestrator/gemini_agent.py`)

**Purpose:** The autonomous brain. Runs in a loop, thinks, calls function tools, responds to events.

```python
# IMPLEMENT THIS MODULE
# Requirements:
# - Use Google Generative AI Python SDK: pip install google-generativeai
# - Model: gemini-2.5-flash (FREE tier — 250 requests/day)
# - Tool use: Gemini function calling (pass function_declarations)
# - Implement continuous autonomous loop
# - Feed real-time classroom events into Gemini's context
# - Handle function call responses and feed results back
# - Maintain conversation history via chat session
# - Inject classroom status every 30 seconds automatically
# - IMPORTANT: Track request count to stay within 250/day free limit

import google.generativeai as genai
from google.generativeai.types import content_types

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# LOOP LOGIC:
# model = genai.GenerativeModel(
#     model_name="gemini-2.5-flash",
#     tools=[{"function_declarations": function_declarations}],
#     system_instruction=SYSTEM_PROMPT
# )
# chat = model.start_chat()
# request_count = 0
#
# while lecture_active and request_count < 240:  # safety margin from 250 limit
#     status = get_class_status()
#     events = get_pending_events()
#     
#     message = build_context_message(status, events)
#     response = chat.send_message(message)
#     request_count += 1
#     
#     # Handle function calls
#     for part in response.parts:
#         if hasattr(part, "function_call") and part.function_call:
#             fn_call = part.function_call
#             result = await execute_tool(fn_call.name, dict(fn_call.args))
#             
#             # Send function result back to Gemini
#             response = chat.send_message(
#                 genai.protos.Content(
#                     parts=[genai.protos.Part(
#                         function_response=genai.protos.FunctionResponse(
#                             name=fn_call.name,
#                             response={"result": result}
#                         )
#                     )]
#                 )
#             )
#             request_count += 1
#     
#     # Check if Gemini decided to end the lecture
#     if "end_lecture" in [p.function_call.name for p in response.parts if hasattr(p, "function_call") and p.function_call]:
#         break
#     
#     await asyncio.sleep(2)  # Pace the loop — saves free tier quota
```

---

### 3. SYSTEM PROMPT (`backend/orchestrator/system_prompt.py`)

```python
# IMPLEMENT THIS — Generate the system prompt dynamically based on lecture config

def build_system_prompt(topic: str, duration_minutes: int, student_count: int, difficulty: str) -> str:
    return f"""
You are Professor AI, an autonomous AI lecturer. You are currently teaching a class of {student_count} students.

LECTURE TOPIC: {topic}
DURATION: {duration_minutes} minutes  
DIFFICULTY LEVEL: {difficulty}

YOUR ROLE:
- Deliver a complete, engaging lecture on the topic
- You control the classroom via tools: speak(), write_on_board(), advance_slide(), warn_student(), etc.
- Act exactly as a real professor would — use the board to explain concepts visually
- Monitor student attention and react accordingly
- Handle student questions when they arise
- Manage classroom discipline if students are disruptive or inattentive

BEHAVIOR RULES:
1. ALWAYS call speak() for anything you say out loud
2. ALWAYS use write_on_board() when explaining something visual or a key formula
3. Check get_class_status() every 2-3 minutes to assess classroom state
4. If a student is distracted for >60 seconds, call warn_student()
5. Break lecture into segments: Introduction → Core Content → Examples → Q&A → Summary
6. Advance slides with advance_slide() at natural transition points
7. Use query_knowledge() if you need to recall specific facts
8. Adjust your pace based on student attention levels
9. End with end_lecture() when done

EFFICIENCY RULES (Important — we have limited API calls per day):
10. Batch multiple actions per turn when possible (speak + write_on_board together)
11. Don't call get_class_status() more than once every 3 minutes
12. Be concise in your reasoning — focus on tool calls

PERSONALITY:
- Authoritative but approachable
- Patient with genuine questions, firm with disruptions
- Uses analogies and real-world examples
- Encourages participation

You have full autonomy. Begin the lecture now.
"""
```

---

### 4. VOICE AGENT (`backend/agents/voice_agent.py`)

```python
# IMPLEMENT THIS MODULE
# 
# TTS (Text to Speech) — OUTPUT to speakers:
#   - Use Coqui TTS: from TTS.api import TTS
#   - Load model once at startup (TTS_MODEL from config)
#   - speak(text) method: synthesize → play via sounddevice or pygame
#   - Support interruption: stop_speaking() kills current audio thread
#   - Emit WebSocket event: {"type": "speaking_start", "text": text}
#   - Emit WebSocket event: {"type": "speaking_end"}
#
# STT (Speech to Text) — INPUT from microphone:
#   - Use OpenAI Whisper: import whisper
#   - Continuously listen in background thread
#   - VAD (Voice Activity Detection): only transcribe when speech detected
#   - When speech detected from student:
#     1. Record until silence (1.5s threshold)
#     2. Transcribe with Whisper
#     3. Emit WebSocket event: {"type": "student_speech", "text": transcript, "timestamp": ...}
#     4. This event gets injected into Gemini's next context window
#   - Use pyaudio for mic capture
#
# IMPLEMENTATION NOTES:
#   - Run TTS and STT in separate threads
#   - Use threading.Event for stop signals
#   - Queue audio chunks with queue.Queue
#   - Don't transcribe AI's own voice (mute STT while TTS is playing)
```

---

### 5. VISION AGENT (`backend/agents/vision_agent.py`)

```python
# IMPLEMENT THIS MODULE
#
# FACE DETECTION (attention monitoring):
#   - Use YOLOv8: from ultralytics import YOLO
#   - Load yolov8n.pt (nano — fast enough for real-time)
#   - Capture frames from webcam at CAMERA_FPS
#   - Detect all faces in frame
#   - For each face: estimate if looking at board (gaze estimation via MediaPipe)
#   - Track attention score per student over rolling 30-second window
#   - If attention_score < 0.3 for >60s → emit distraction event
#
# ATTENDANCE (face recognition):
#   - Use DeepFace: from deepface import DeepFace
#   - Student photos stored in data/student_photos/{student_id}.jpg
#   - scan_attendance() method:
#     1. Capture frame
#     2. Run DeepFace.find() against student_photos directory
#     3. Return matched student IDs as present
#     4. Update attendance in SQLite
#
# EVENTS EMITTED (WebSocket):
#   {"type": "student_distracted", "student_id": str, "duration_seconds": int}
#   {"type": "attendance_updated", "present": [...], "absent": [...]}
#   {"type": "unknown_person_detected", "count": int}
#
# IMPLEMENTATION NOTES:
#   - Run in separate thread/process (CPU intensive)
#   - Limit to CAMERA_FPS processing rate
#   - Cache face recognition results (don't re-identify every frame)
#   - Use student_id = "unknown_N" for unrecognized faces
```

---

### 6. KNOWLEDGE AGENT (`backend/agents/knowledge_agent.py`)

```python
# IMPLEMENT THIS MODULE
#
# PURPOSE: RAG (Retrieval Augmented Generation) over lecture materials
#
# SETUP:
#   - Use LlamaIndex + ChromaDB
#   - On startup: ingest all files from data/knowledge_base/
#   - Supported formats: PDF, TXT, MD, DOCX
#   - Create embeddings with EMBEDDING_MODEL (all-MiniLM-L6-v2)
#   - Store in ChromaDB at CHROMA_PATH
#
# METHODS:
#   query(query_text: str, top_k: int = 3) -> list[dict]
#     - Semantic search over knowledge base
#     - Returns top_k relevant chunks with source info
#
#   add_document(file_path: str) -> bool
#     - Ingest new document at runtime
#     - Re-index and make available immediately
#
#   get_topic_outline(topic: str) -> list[str]
#     - Generate lecture outline from knowledge base
#     - Returns ordered list of subtopics to cover
#
# INITIALIZATION:
#   - Check if ChromaDB index exists → load it
#   - If not → ingest all documents in knowledge_base/
#   - Log document count and chunk count on startup
```

---

### 7. VIRTUAL BOARD (`frontend/src/components/VirtualBoard.jsx`)

```jsx
// IMPLEMENT THIS COMPONENT
//
// PURPOSE: AI-controlled interactive whiteboard displayed on projector
//
// LIBRARY: react-konva (Konva.js canvas)
// npm install react-konva konva
//
// FEATURES:
//   - Receives write commands via WebSocket
//   - Renders text, equations (KaTeX), and diagrams
//   - Supports: Text nodes, Arrow nodes, Box nodes, Circle nodes, Line nodes
//   - Animated appearance (each element fades in as Gemini "writes" it)
//   - Color coding: definitions=blue, formulas=orange, examples=green, warnings=red
//   - Clear board: fade out all elements
//   - Highlight: pulse animation on specified element
//   - Auto-layout: left-to-right, top-to-bottom with smart spacing
//
// WEBSOCKET EVENTS TO HANDLE:
//   {"type": "board_write", "content": str, "style": "normal|formula|heading|example", "position": "auto|{x,y}"}
//   {"type": "board_clear"}
//   {"type": "board_highlight", "element_id": str}
//   {"type": "board_draw", "diagram_type": str, "data": object}
//
// MATH RENDERING:
//   npm install react-katex katex
//   Detect LaTeX in content (between $...$ or $$...$$) → render with KaTeX
//
// EXPORT: default VirtualBoard
// PROPS: { width: number, height: number, wsUrl: string }
```

---

### 8. DASHBOARD (`frontend/src/pages/Dashboard.jsx`)

```jsx
// IMPLEMENT THIS PAGE
//
// PURPOSE: Instructor/operator control panel
//
// LAYOUT: Split into 4 quadrants
//   TOP-LEFT:    Live camera feed + attention heatmap overlay
//   TOP-RIGHT:   Attendance grid (photo + name + status per student)
//   BOTTOM-LEFT: Live transcript feed (what Gemini is saying, scrolling)
//   BOTTOM-RIGHT: Controls + alerts log
//
// CONTROLS:
//   - [Start Lecture] button → POST /api/lecture/start {topic, duration, difficulty}
//   - [Pause] / [Resume] button
//   - [End Lecture] button
//   - Topic input field
//   - Difficulty selector (beginner/intermediate/advanced)
//   - Duration slider (15 to 90 minutes)
//   - API Quota indicator: "Remaining: 187/250 requests today"
//
// REAL-TIME DATA (WebSocket):
//   - Transcript updates: append to feed
//   - Student warnings: show in alerts log with timestamp
//   - Attendance updates: refresh attendance grid
//   - Board events: show in activity feed
//   - Lecture status: update status indicator
//   - Quota updates: show remaining API calls
//
// STYLE: Dark theme, professional UI, green accent for active/present, red for alerts
```

---

### 9. PROJECTOR VIEW (`frontend/src/pages/Projector.jsx`)

```jsx
// IMPLEMENT THIS PAGE
//
// PURPOSE: Fullscreen display on classroom projector
// URL: /projector (open this URL in browser, then press F11 for fullscreen)
//
// LAYOUT: Split screen
//   LEFT 60%:  VirtualBoard component
//   RIGHT 40%: SlideViewer component (reveal.js iframe or custom)
//
// ALSO SHOWS:
//   - Professor status bar at top: "🎓 Professor AI — [SPEAKING] Introduction to Neural Networks"
//   - Current lecture time elapsed
//   - Student Q&A alert: when Gemini calls on a student, their name flashes
//   - Subtle animated background (very dark, not distracting)
//
// FULL SCREEN BEHAVIOR:
//   - No scrollbars
//   - Cursor hidden after 3s inactivity
//   - Keyboard shortcut F to toggle fullscreen
```

---

### 10. FASTAPI BACKEND (`backend/main.py`)

```python
# IMPLEMENT THIS — Main FastAPI application
#
# ROUTES:
#   GET  /                          → health check
#   POST /api/lecture/start         → start autonomous lecture
#   POST /api/lecture/pause         → pause lecture
#   POST /api/lecture/resume        → resume lecture
#   POST /api/lecture/end           → end lecture
#   GET  /api/lecture/status        → current lecture state + API quota remaining
#   GET  /api/students              → list all students
#   POST /api/students              → add student (with photo upload)
#   GET  /api/students/{id}         → get student details
#   POST /api/knowledge/upload      → upload document to knowledge base
#   GET  /api/attendance/{session}  → get attendance for session
#   GET  /api/quota                 → remaining Gemini API calls today
#   WebSocket /ws                   → real-time event stream
#
# STARTUP SEQUENCE:
#   1. Validate GOOGLE_API_KEY is set
#   2. Initialize SQLite database
#   3. Start ChromaDB and ingest knowledge base
#   4. Load AI models (YOLOv8, DeepFace, Whisper, Coqui TTS)
#   5. Initialize Gemini model with function declarations
#   6. Start Vision Agent background thread
#   7. Start Voice Agent (STT listener)
#   8. Start WebSocket hub
#   9. Ready!
#
# lecture/start REQUEST BODY:
#   {
#     "topic": "Introduction to Machine Learning",
#     "duration_minutes": 45,
#     "difficulty": "intermediate",
#     "student_ids": ["s001", "s002", ...]   // optional, for targeted attendance
#   }
```

---

## DATA MODELS

```python
# backend/models/student.py
@dataclass
class Student:
    id: str                    # e.g. "s001"
    name: str
    photo_path: str            # path to face photo
    email: str
    attention_score: float     # 0.0 to 1.0 (rolling average)
    is_present: bool
    warning_count: int         # warnings issued this session
    last_seen: datetime

# backend/models/lecture.py
@dataclass
class LectureSession:
    id: str                    # UUID
    topic: str
    difficulty: str
    started_at: datetime
    ended_at: Optional[datetime]
    status: str                # "starting" | "active" | "paused" | "ended"
    duration_minutes: int
    slides_generated: int
    tool_calls_made: int
    api_calls_used: int        # Track Gemini API usage
    student_ids: List[str]

# backend/models/event.py
@dataclass
class ClassroomEvent:
    type: str                  # "student_speech" | "distraction" | "question" | etc.
    timestamp: datetime
    data: dict
    handled: bool
    injected_to_gemini: bool
```

---

## WEBSOCKET EVENT TYPES

```typescript
// All events have this shape:
type WSEvent = {
  type: string;
  timestamp: string;  // ISO 8601
  data: object;
}

// Event types:
"lecture_started"         // data: { topic, session_id, student_count }
"lecture_paused"          // data: {}
"lecture_ended"           // data: { duration_seconds, tool_calls, api_calls_used }
"speaking_start"          // data: { text: string }
"speaking_end"            // data: { duration_ms: number }
"board_write"             // data: { content, style, position, element_id }
"board_clear"             // data: {}
"board_draw"              // data: { diagram_type, diagram_data, element_id }
"slide_advanced"          // data: { slide_number, total_slides }
"student_warned"          // data: { student_id, student_name, reason, severity }
"student_called"          // data: { student_id, student_name, question }
"student_distracted"      // data: { student_id, duration_seconds }
"attendance_updated"      // data: { present: string[], absent: string[] }
"student_speech"          // data: { transcript: string, student_id?: string }
"gemini_thinking"         // data: {} — Gemini is processing
"tool_called"             // data: { tool_name, args }
"tool_result"             // data: { tool_name, result }
"class_status_update"     // data: { attentive_count, distracted_count, time_elapsed }
"quota_update"            // data: { used: number, remaining: number, limit: 250 }
```

---

## INSTALLATION & SETUP

```bash
# 1. Clone and setup
git clone <repo>
cd ai-lecturer

# 2. Python dependencies
pip install google-generativeai fastapi uvicorn websockets \
            openai-whisper TTS pyaudio sounddevice \
            ultralytics deepface opencv-python \
            transformers sentence-transformers \
            llama-index chromadb \
            sqlalchemy python-dotenv pillow

# 3. Frontend dependencies
cd frontend
npm install react react-dom react-konva konva react-katex katex \
            react-router-dom tailwindcss vite

# 4. Download AI models (happens automatically on first run, or manually:)
python -c "import whisper; whisper.load_model('base')"
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 5. Get FREE Gemini API Key
# Go to: https://aistudio.google.com/app/apikey
# Click "Create API Key" — completely free, no credit card needed
# Copy the key into your .env file

# 6. Add students (photos)
# Place student face photos in data/student_photos/{student_id}.jpg
# Add student records via POST /api/students or directly in SQLite

# 7. Add lecture materials
# Drop PDFs, docs, or text files into data/knowledge_base/

# 8. Run
cp .env.example .env   # add your GOOGLE_API_KEY
python backend/main.py  # starts backend on port 8000
cd frontend && npm run dev  # starts frontend on port 5173

# 9. Open:
#   Dashboard:  http://localhost:5173/
#   Projector:  http://localhost:5173/projector  (show on projector, F11 fullscreen)
```

---

## AUTONOMOUS LECTURE FLOW (Step by Step)

```
1. Instructor opens Dashboard → enters topic, duration, difficulty → clicks Start
2. Backend: creates LectureSession, runs scan_attendance(), builds system prompt
3. Gemini 2.5 Flash starts autonomous loop:
   
   TURN 1: Gemini calls scan_attendance() → knows who is present
   TURN 2: Gemini calls speak("Good morning class...") + advance_slide()
   TURN 3: Gemini calls write_on_board("Today's Topic: Neural Networks", style="heading")
   TURN 4: Gemini calls speak("Let's start with the basics...")
   TURN 5: Gemini calls write_on_board("f(x) = wx + b", style="formula")
   ...
   [30 seconds later — vision agent detects student looking at phone]
   Event injected → "Student s003 has been distracted for 45 seconds"
   Gemini calls warn_student("s003", "Please put your phone away", "mild")
   Gemini calls speak("As I was saying, the gradient is...")
   ...
   [Student raises hand / speaks into mic]
   STT transcribes: "Can you explain backpropagation?"
   Event injected → Gemini acknowledges and explains
   Gemini calls write_on_board("Backpropagation: ∂L/∂w", style="formula")
   Gemini calls draw_diagram("flowchart", {nodes: ["Input", "Forward", "Loss", "Backward"]})
   ...
   [At 80% of duration]
   Gemini calls ask_class("Any final questions?")
   Gemini calls speak("Let me summarize what we covered today...")
   Gemini calls end_lecture()

4. Session logged to database, attendance finalized, transcript saved
5. Dashboard shows: "Lecture complete — used 67/250 API calls today"
```

---

## FREE TIER QUOTA MANAGEMENT

**This is critical since we're on Gemini's free tier (250 requests/day).**

```python
# backend/orchestrator/quota_manager.py
# IMPLEMENT THIS MODULE

class QuotaManager:
    DAILY_LIMIT = 250
    SAFETY_MARGIN = 10  # Reserve 10 calls for emergencies
    
    def __init__(self):
        self.calls_today = 0
        self.reset_date = date.today()
    
    def can_make_call(self) -> bool:
        self._check_reset()
        return self.calls_today < (self.DAILY_LIMIT - self.SAFETY_MARGIN)
    
    def record_call(self):
        self.calls_today += 1
        # Broadcast quota update via WebSocket
    
    def remaining(self) -> int:
        return self.DAILY_LIMIT - self.calls_today
    
    def estimate_calls_for_lecture(self, duration_minutes: int) -> int:
        # ~1.5 calls per minute of lecture
        return int(duration_minutes * 1.5)
    
    def _check_reset(self):
        if date.today() > self.reset_date:
            self.calls_today = 0
            self.reset_date = date.today()

# OPTIMIZATION STRATEGIES:
# 1. Batch multiple tool calls per Gemini turn (speak + write together)
# 2. Increase sleep between loop iterations (2-3 seconds)
# 3. Only inject class status every 3 minutes instead of 30 seconds
# 4. Cache knowledge queries — don't re-query same topic
# 5. Pre-generate lecture outline before starting the loop
```

---

## KEY IMPLEMENTATION NOTES FOR COPILOT

1. **Gemini function calling:** Use `google.generativeai` SDK. Pass `tools=[{"function_declarations": [...]}]` to `GenerativeModel()`. Parse `response.parts` for `function_call` objects. Send back `function_response` via `chat.send_message()`.

2. **Tool pattern:** Gemini does NOT execute code directly. It returns function call names + arguments as structured data. Your tool registry maps function names → Python functions → hardware/UI actions.

3. **Async everything:** All agents run async. Use `asyncio.gather()` to start all agents. Use `asyncio.Queue` for event passing between agents and Gemini.

4. **WebSocket broadcast:** Every action (speak, write, warn, etc.) MUST broadcast a WebSocket event so the frontend updates in real-time.

5. **Thread safety:** Vision Agent and Voice Agent run in threads. Use thread-safe queues to communicate with the async FastAPI event loop. Use `asyncio.run_coroutine_threadsafe()`.

6. **Context management:** Gemini `chat.send_message()` maintains history automatically. Inject latest class status at start of each turn. Keep turns focused and concise to save tokens.

7. **Projector output:** The /projector page is a browser tab. Use window.open() or a second monitor to display it. Gemini controls it entirely via WebSocket events — no human needed.

8. **Error handling:** If a tool fails (e.g., TTS crash), return error to Gemini in function_response. Gemini should handle gracefully and try alternative action.

9. **Demo mode:** Add `DEMO_MODE=true` env var that uses mock camera/mic data so the system can be demoed without real hardware.

10. **Quota awareness:** ALWAYS check `QuotaManager.can_make_call()` before sending to Gemini. Show remaining quota on Dashboard. Warn instructor if quota is running low.

---

## EXPO DEMO CHECKLIST

- [ ] FREE Gemini API key generated at https://aistudio.google.com/app/apikey
- [ ] .env has valid GOOGLE_API_KEY
- [ ] Tested quota: run a quick 5-min test lecture to verify API calls work
- [ ] Student photos registered in database
- [ ] Knowledge base PDFs loaded (lecture topic material)
- [ ] Camera tested (face detection working)
- [ ] Speakers tested (TTS output clear)
- [ ] Mic tested (Whisper transcription working)  
- [ ] Projector connected (browser on /projector URL, fullscreen)
- [ ] Dashboard open on laptop screen
- [ ] Demo topic chosen and materials in knowledge_base/
- [ ] "Plant" a volunteer to ask a question or pretend to be distracted
- [ ] Practice the 3-minute demo flow at least twice
- [ ] Check remaining Gemini quota before demo day (need ~80 calls per demo)

---

## FALLBACK PLAN (If Gemini Free Tier Has Issues)

If Google changes the free tier or you hit rate limits on demo day:

**Option A: Switch to Gemini 2.5 Flash-Lite** (1,000 req/day free — more headroom, slightly lower quality)
```python
# Just change in .env:
GEMINI_MODEL=gemini-2.5-flash-lite
```

**Option B: Switch to local Ollama + Llama 3** (unlimited, needs decent hardware)
```python
# pip install openai
from openai import OpenAI
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
# Requires: brew install ollama && ollama pull llama3:8b
```

**Option C: Use OpenAI free credits** ($5 free for new accounts)
```python
# pip install openai
from openai import OpenAI
client = OpenAI(api_key="your_key")
# Use model="gpt-4o-mini" for cheapest option
```

---

*This specification is designed to be fed directly to GitHub Copilot to generate production-ready code for each module. Every technology is free or open-source. Implement modules in this order: Tool Registry → Gemini Agent → Voice Agent → Vision Agent → Knowledge Agent → Frontend.*
