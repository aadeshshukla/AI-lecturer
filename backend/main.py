"""FastAPI application entry point for the AI Autonomous Lecturer backend.

Exposes:
  - GET  /                         → serves frontend (index.html)
  - GET  /projector                → serves projector view (projector.html)
  - POST /api/lecture/start        → start autonomous lecture
  - POST /api/lecture/pause        → pause lecture
  - POST /api/lecture/resume       → resume lecture
  - POST /api/lecture/end          → end lecture
  - GET  /api/lecture/status       → current lecture state
  - GET  /api/students             → list all students (in-memory)
  - POST /api/students             → add a student (JSON, name only)
  - WebSocket /ws                  → real-time event stream
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import uvicorn
from fastapi import (
    APIRouter,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import config
from backend.models.event import ClassroomEvent
from backend.models.lecture import LectureSession
from backend.models.student import Student
from backend.orchestrator.gemini_agent import GeminiOrchestrator
from backend.orchestrator.lecture_state import lecture_state
from backend.websocket.events import create_event
from backend.websocket.hub import ws_hub

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Demo students seeded on startup
# ---------------------------------------------------------------------------

_DEMO_STUDENTS = [
    {"name": "Alice Chen"},
    {"name": "Bob Martinez"},
    {"name": "Carol Singh"},
    {"name": "David Kim"},
    {"name": "Eva Patel"},
]

# ---------------------------------------------------------------------------
# In-memory student registry (persists for process lifetime)
# ---------------------------------------------------------------------------

_students: dict[str, Student] = {}


def _seed_demo_students() -> None:
    """Populate the in-memory student registry with demo students."""
    for s in _DEMO_STUDENTS:
        sid = str(uuid.uuid4())
        _students[sid] = Student(
            id=sid,
            name=s["name"],
            photo_path="",
            email="",
        )
    logger.info("Seeded %d demo students", len(_DEMO_STUDENTS))


# ---------------------------------------------------------------------------
# Orchestrator singleton
# ---------------------------------------------------------------------------

gemini_orchestrator = GeminiOrchestrator()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: seed demo students. Shutdown: stop orchestrator."""
    _seed_demo_students()
    logger.info("AI Autonomous Lecturer backend started.")
    yield
    try:
        await gemini_orchestrator.stop_lecture()
    except Exception:
        pass
    logger.info("AI Autonomous Lecturer backend shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Autonomous Lecturer",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request schemas
# ---------------------------------------------------------------------------

class StartLectureRequest(BaseModel):
    topic: str
    duration_minutes: int = 45
    difficulty: str = "intermediate"


class AddStudentRequest(BaseModel):
    name: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "name": "AI Autonomous Lecturer", "version": "2.0.0"}


@router.post("/api/lecture/start")
async def start_lecture(body: StartLectureRequest):
    """Start an autonomous lecture session."""
    if lecture_state.status not in ("idle", "ended"):
        raise HTTPException(
            status_code=409,
            detail=f"Lecture already in progress (status: {lecture_state.status})",
        )

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    session = LectureSession(
        id=session_id,
        topic=body.topic,
        difficulty=body.difficulty,
        started_at=now,
        status="starting",
        duration_minutes=body.duration_minutes,
    )

    await lecture_state.start_session(session)

    students: List[Student] = list(_students.values())
    await lecture_state.register_students(students)

    asyncio.create_task(
        gemini_orchestrator.start_lecture(
            topic=body.topic,
            duration_minutes=body.duration_minutes,
            difficulty=body.difficulty,
            student_count=len(students),
            session_id=session_id,
        )
    )

    await ws_hub.broadcast(
        create_event(
            "lecture_started",
            {
                "session_id": session_id,
                "topic": body.topic,
                "duration_minutes": body.duration_minutes,
                "difficulty": body.difficulty,
            },
        )
    )

    logger.info("Lecture started: session=%s topic=%s", session_id, body.topic)
    return {"session_id": session_id, "status": "started"}


@router.post("/api/lecture/pause")
async def pause_lecture():
    """Pause the currently running lecture."""
    if lecture_state.status != "active":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot pause — current status: {lecture_state.status}",
        )
    await lecture_state.update_status("paused")
    await ws_hub.broadcast(create_event("lecture_paused", {}))
    return {"status": "paused"}


@router.post("/api/lecture/resume")
async def resume_lecture():
    """Resume a paused lecture."""
    if lecture_state.status != "paused":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot resume — current status: {lecture_state.status}",
        )
    await lecture_state.update_status("active")
    await ws_hub.broadcast(create_event("lecture_resumed", {}))
    return {"status": "active"}


@router.post("/api/lecture/end")
async def end_lecture():
    """End the current lecture session."""
    if lecture_state.status in ("idle",):
        raise HTTPException(status_code=409, detail="No active lecture to end")

    try:
        await gemini_orchestrator.stop_lecture()
    except Exception as exc:
        logger.warning("gemini_orchestrator.stop_lecture() error: %s", exc)

    session = lecture_state.session
    await lecture_state.end_session()

    await ws_hub.broadcast(
        create_event("lecture_ended", {"session_id": session.id if session else None})
    )
    return {"status": "ended"}


def _ensure_utc(dt: datetime) -> datetime:
    """Return *dt* as a UTC-aware datetime, assuming UTC if tzinfo is absent."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/api/lecture/status")
async def get_lecture_status():
    """Return the current lecture state."""
    session = lecture_state.session
    time_elapsed = 0
    if session and session.started_at:
        elapsed = datetime.now(timezone.utc) - _ensure_utc(session.started_at)
        time_elapsed = int(elapsed.total_seconds())

    students = list(lecture_state.students.values())
    attention_scores = [s.attention_score for s in students if s.is_present]
    attention_average = (
        sum(attention_scores) / len(attention_scores) if attention_scores else 0.0
    )

    return {
        "status": lecture_state.status,
        "topic": session.topic if session else None,
        "session_id": session.id if session else None,
        "time_elapsed": time_elapsed,
        "current_slide": lecture_state.current_slide,
        "student_count": len(students),
        "students_present": sum(1 for s in students if s.is_present),
        "attention_average": round(attention_average, 3),
        "transcript": list(lecture_state.transcript)[-20:],
    }


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

@router.get("/api/students")
async def list_students():
    """Return all registered students."""
    return [
        {
            "id": s.id,
            "name": s.name,
            "attention_score": s.attention_score,
            "is_present": s.is_present,
            "warning_count": s.warning_count,
        }
        for s in _students.values()
    ]


@router.post("/api/students", status_code=201)
async def add_student(body: AddStudentRequest):
    """Add a new student (name only)."""
    student_id = str(uuid.uuid4())
    student = Student(
        id=student_id,
        name=body.name,
        photo_path="",
        email="",
    )
    _students[student_id] = student
    logger.info("Student added: id=%s name=%s", student_id, body.name)
    return {
        "id": student.id,
        "name": student.name,
        "attention_score": student.attention_score,
        "is_present": student.is_present,
        "warning_count": student.warning_count,
    }


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket endpoint for frontend clients."""
    await ws_hub.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            msg_type = msg.get("type")

            if msg_type == "student_speech":
                text = msg.get("text", "")
                student_id = msg.get("student_id", "unknown")
                event = ClassroomEvent(
                    type="student_speech",
                    data={"text": text, "student_id": student_id},
                )
                await lecture_state.add_event(event)
                await ws_hub.broadcast(
                    create_event(
                        "student_speech",
                        {"text": text, "student_id": student_id},
                    )
                )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        ws_hub.disconnect(websocket)


# ---------------------------------------------------------------------------
# Mount API router
# ---------------------------------------------------------------------------

app.include_router(router)

# ---------------------------------------------------------------------------
# Serve frontend static files (must come after API routes)
# ---------------------------------------------------------------------------

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if _FRONTEND_DIR.exists():
    # Serve /projector → projector.html
    @app.get("/projector")
    async def projector_page():
        return FileResponse(_FRONTEND_DIR / "projector.html")

    # Mount static assets (css, js, etc.)
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=config.BACKEND_PORT)
