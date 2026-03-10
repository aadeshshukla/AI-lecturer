"""Entry point for the AI Autonomous Lecturer backend.

TODO PR3: Implement full FastAPI application with:
  - GET  /                       → health check
  - POST /api/lecture/start      → start autonomous lecture
  - POST /api/lecture/pause      → pause lecture
  - POST /api/lecture/resume     → resume lecture
  - POST /api/lecture/end        → end lecture
  - GET  /api/lecture/status     → current lecture state + API quota
  - GET  /api/students           → list all students
  - POST /api/students           → add student (with photo upload)
  - GET  /api/students/{id}      → get student details
  - POST /api/knowledge/upload   → upload document to knowledge base
  - GET  /api/attendance/{session} → get attendance for session
  - GET  /api/quota              → remaining Gemini API calls today
  - WebSocket /ws                → real-time event stream
"""
