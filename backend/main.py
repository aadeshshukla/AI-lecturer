"""FastAPI application entry point for the AI Autonomous Lecturer backend.

Exposes:
  - GET  /                         → health check
  - POST /api/lecture/start        → start autonomous lecture
  - POST /api/lecture/pause        → pause lecture
  - POST /api/lecture/resume       → resume lecture
  - POST /api/lecture/end          → end lecture
  - GET  /api/lecture/status       → current lecture state + API quota
  - GET  /api/students             → list all students
  - POST /api/students             → add student (with photo upload)
  - GET  /api/students/{id}        → get student details
  - POST /api/knowledge/upload     → upload document to knowledge base
  - GET  /api/attendance/{session} → attendance data for a session
  - GET  /api/quota                → remaining Gemini API calls today
  - WebSocket /ws                  → real-time event stream
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

import uvicorn
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import config
from backend.agents.attention_agent import AttentionAgent
from backend.agents.knowledge_agent import KnowledgeAgent
from backend.agents.vision_agent import VisionAgent
from backend.agents.voice_agent import VoiceAgent
from backend.database.db import get_db, init_db
from backend.database.sessions import (
    create_session as db_create_session,
    end_session as db_end_session,
    get_session as db_get_session,
)
from backend.database.students import (
    create_student,
    get_all_students,
    get_student,
)
from backend.models.event import ClassroomEvent
from backend.models.lecture import LectureSession
from backend.models.student import Student
from backend.orchestrator.gemini_agent import GeminiOrchestrator
from backend.orchestrator.lecture_state import lecture_state
from backend.orchestrator.quota_manager import quota_manager
from backend.websocket.events import create_event
from backend.websocket.hub import ws_hub

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton agent instances (created once per process lifetime)
# ---------------------------------------------------------------------------
gemini_orchestrator = GeminiOrchestrator()
voice_agent = VoiceAgent()
vision_agent = VisionAgent()
attention_agent = AttentionAgent()
knowledge_agent = KnowledgeAgent()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise database. Shutdown: stop all agents."""
    init_db()
    logger.info("AI Autonomous Lecturer backend started.")
    yield
    # Cleanup on shutdown
    try:
        vision_agent.stop()
    except Exception:
        pass
    try:
        voice_agent.stop_listening()
    except Exception:
        pass
    logger.info("AI Autonomous Lecturer backend shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Autonomous Lecturer",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{config.FRONTEND_PORT}",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "name": "AI Autonomous Lecturer", "version": "1.0.0"}


@router.post("/api/lecture/start")
async def start_lecture(
    body: StartLectureRequest,
    db: Session = Depends(get_db),
):
    """Start an autonomous lecture session."""
    if lecture_state.status not in ("idle", "ended"):
        raise HTTPException(
            status_code=409,
            detail=f"Lecture already in progress (status: {lecture_state.status})",
        )

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Persist session in DB
    db_session = LectureSession(
        id=session_id,
        topic=body.topic,
        difficulty=body.difficulty,
        started_at=now,
        status="starting",
        duration_minutes=body.duration_minutes,
    )
    try:
        db_create_session(db, db_session)
    except Exception as exc:
        logger.error("Failed to create session in DB: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create session") from exc

    # Initialise in-memory lecture state
    await lecture_state.start_session(db_session)

    # Load students from DB and register them
    students: List[Student] = get_all_students(db)
    await lecture_state.register_students(students)

    # Start peripheral agents (errors are non-fatal in demo mode)
    try:
        vision_agent.start()
    except Exception as exc:
        logger.warning("VisionAgent.start() failed (non-fatal): %s", exc)

    try:
        voice_agent.start_listening()
    except Exception as exc:
        logger.warning("VoiceAgent.start_listening() failed (non-fatal): %s", exc)

    try:
        await knowledge_agent.initialize()
    except Exception as exc:
        logger.warning("KnowledgeAgent.initialize() failed (non-fatal): %s", exc)

    # Launch Gemini autonomous loop as a background task
    asyncio.create_task(
        gemini_orchestrator.start_lecture(
            topic=body.topic,
            duration_minutes=body.duration_minutes,
            difficulty=body.difficulty,
            student_count=len(students),
            session_id=session_id,
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
    return {"status": "active"}


@router.post("/api/lecture/end")
async def end_lecture(db: Session = Depends(get_db)):
    """End the current lecture session."""
    if lecture_state.status in ("idle",):
        raise HTTPException(status_code=409, detail="No active lecture to end")

    # Stop Gemini loop
    try:
        await gemini_orchestrator.stop_lecture()
    except Exception as exc:
        logger.warning("gemini_orchestrator.stop_lecture() error: %s", exc)

    # Stop agents
    try:
        vision_agent.stop()
    except Exception as exc:
        logger.warning("VisionAgent.stop() error: %s", exc)

    try:
        voice_agent.stop_listening()
    except Exception as exc:
        logger.warning("VoiceAgent.stop_listening() error: %s", exc)

    # Update in-memory state
    session = lecture_state.session
    await lecture_state.end_session()

    # Persist to DB
    if session:
        try:
            db_end_session(db, session.id)
        except Exception as exc:
            logger.warning("db_end_session error: %s", exc)

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
        "api_calls_used": quota_manager.calls_today,
        "api_calls_remaining": quota_manager.remaining(),
        "transcript": list(lecture_state.transcript)[-20:],
    }


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

@router.get("/api/students")
async def list_students(db: Session = Depends(get_db)):
    """Return all registered students."""
    students = get_all_students(db)
    return [
        {
            "id": s.id,
            "name": s.name,
            "email": s.email,
            "photo_path": s.photo_path,
            "attention_score": s.attention_score,
            "is_present": s.is_present,
            "warning_count": s.warning_count,
        }
        for s in students
    ]


@router.post("/api/students", status_code=201)
async def add_student(
    name: str = Form(...),
    email: str = Form(...),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Add a new student with optional photo upload."""
    student_id = str(uuid.uuid4())
    photo_path = ""

    if photo and photo.filename:
        photos_dir = os.path.join("data", "student_photos")
        os.makedirs(photos_dir, exist_ok=True)
        ext = os.path.splitext(photo.filename)[-1] or ".jpg"
        photo_path = os.path.join(photos_dir, f"{student_id}{ext}")
        try:
            content = await photo.read()
            with open(photo_path, "wb") as fh:
                fh.write(content)
        except Exception as exc:
            logger.error("Failed to save student photo: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to save photo") from exc

    student = Student(
        id=student_id,
        name=name,
        email=email,
        photo_path=photo_path,
    )
    try:
        created = create_student(db, student)
    except Exception as exc:
        logger.error("Failed to create student: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create student") from exc

    return {
        "id": created.id,
        "name": created.name,
        "email": created.email,
        "photo_path": created.photo_path,
        "attention_score": created.attention_score,
        "is_present": created.is_present,
        "warning_count": created.warning_count,
    }


@router.get("/api/students/{student_id}")
async def get_student_detail(student_id: str, db: Session = Depends(get_db)):
    """Return details for a single student."""
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return {
        "id": student.id,
        "name": student.name,
        "email": student.email,
        "photo_path": student.photo_path,
        "attention_score": student.attention_score,
        "is_present": student.is_present,
        "warning_count": student.warning_count,
        "last_seen": student.last_seen.isoformat() if student.last_seen else None,
    }


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

@router.post("/api/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    """Upload a document to the knowledge base for RAG retrieval."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    kb_dir = os.path.join("data", "knowledge_base")
    os.makedirs(kb_dir, exist_ok=True)
    dest_path = os.path.join(kb_dir, file.filename)

    try:
        content = await file.read()
        with open(dest_path, "wb") as fh:
            fh.write(content)
    except Exception as exc:
        logger.error("Failed to save knowledge file: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save file") from exc

    try:
        await knowledge_agent.add_document(dest_path)
    except Exception as exc:
        logger.warning("KnowledgeAgent.add_document() error (non-fatal): %s", exc)

    return {"status": "ingested", "filename": file.filename}


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

@router.get("/api/attendance/{session_id}")
async def get_attendance(session_id: str, db: Session = Depends(get_db)):
    """Return attendance data for a given session."""
    session = db_get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # If this is the currently active session, pull from live state
    if (
        lecture_state.session
        and lecture_state.session.id == session_id
    ):
        students = list(lecture_state.students.values())
    else:
        students = get_all_students(db)

    return {
        "session_id": session_id,
        "topic": session.topic,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "students": [
            {
                "id": s.id,
                "name": s.name,
                "is_present": s.is_present,
                "attention_score": s.attention_score,
                "warning_count": s.warning_count,
            }
            for s in students
        ],
    }


# ---------------------------------------------------------------------------
# Quota
# ---------------------------------------------------------------------------

@router.get("/api/quota")
async def get_quota():
    """Return current Gemini API quota usage."""
    return {
        "used": quota_manager.calls_today,
        "remaining": quota_manager.remaining(),
        "limit": quota_manager.DAILY_LIMIT,
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

            if msg_type == "inject_speech":
                # Demo: simulate student speaking
                text = msg.get("text", "")
                student_id = msg.get("student_id", "unknown")
                event = ClassroomEvent(
                    type="student_speech",
                    data={"text": text, "student_id": student_id},
                )
                await lecture_state.add_event(event)
                # Also broadcast to other clients
                ws_event = create_event(
                    "student_speech",
                    {"text": text, "student_id": student_id},
                )
                await ws_hub.broadcast(ws_event)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        ws_hub.disconnect(websocket)


# ---------------------------------------------------------------------------
# Mount router
# ---------------------------------------------------------------------------

app.include_router(router)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=config.BACKEND_PORT)
