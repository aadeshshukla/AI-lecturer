# 📋 Expo Demo Checklist — AI Autonomous Lecturer

> Print this page before your demo. Check off each item as you complete it.

---

## 🔑 Before Demo Day (Setup)

- [ ] Generate a **free Gemini API key** at https://aistudio.google.com/app/apikey
- [ ] Copy `.env.example` to `.env` and paste the API key into `GOOGLE_API_KEY`
- [ ] Install Python dependencies: `pip install -r requirements.txt`
- [ ] Install frontend dependencies: `cd frontend && npm install`
- [ ] **Test quota:** Run a quick 5-minute test lecture to verify API calls work
- [ ] Register student photos in the database (or set `DEMO_MODE=true` to skip)
- [ ] Load lecture topic material (PDFs) into `data/knowledge_base/`

---

## 🖥️ Hardware Setup (Real Classroom)

- [ ] **Camera** tested — face detection working (DroidCam WiFi or USB webcam)
- [ ] **Speakers** tested — TTS output is clear
- [ ] **Microphone** tested — Whisper transcription is working
- [ ] **Projector** connected via HDMI; open `/projector` URL in browser and press **F11** for fullscreen

---

## 🧪 Demo Mode (Expo / No Hardware)

- [ ] Set `DEMO_MODE=true` in `.env`
- [ ] Confirm 5 demo students auto-seed on startup (Alice, Bob, Carol, David, Eve)
- [ ] Confirm mock mic injects questions every 30–60 seconds

---

## 🚀 Day-Of Checklist

- [ ] Backend is running: `python -m uvicorn backend.main:app --port 8000`
- [ ] Frontend is running: `cd frontend && npm run dev`
- [ ] **Dashboard** is open on laptop screen: http://localhost:5173
- [ ] **Projector view** is open in fullscreen on projector display: http://localhost:5173/projector
- [ ] Checked remaining Gemini quota (need ~80 calls per demo)
- [ ] Chose a demo topic and confirmed materials are in `data/knowledge_base/`
- [ ] "Plant" a volunteer to ask a question or pretend to be distracted (for a live demo)
- [ ] **Practised** the 3-minute demo flow at least **twice**

---

## 🎬 3-Minute Demo Flow

1. **Open Dashboard** → show student attendance grid
2. **Click "Start Lecture"** → enter topic (e.g., "Introduction to Neural Networks")
3. Watch the **Virtual Board** and **Slide Viewer** update autonomously
4. Point out **real-time attention scores** updating per student
5. **Ask a question** (or wait for mock mic to inject one) and show Gemini responding
6. Show **Projector view** on the second screen
7. End the lecture via the Dashboard

---

## 🔄 Fallback Plans

### Option A — Switch to Gemini 2.5 Flash-Lite (1,000 req/day free)
```
# In .env:
GEMINI_MODEL=gemini-2.5-flash-lite
```

### Option B — Local Ollama + Llama 3 (unlimited, needs decent GPU)
```bash
brew install ollama
ollama pull llama3:8b
# Update backend/orchestrator/gemini_agent.py to use OpenAI-compatible client
# pointing at http://localhost:11434/v1
```

### Option C — OpenAI ($5 free credits for new accounts)
```
# In .env:
# Update gemini_agent.py to use openai client with model="gpt-4o-mini"
```

---

## 📞 Quick Troubleshooting

| Problem | Fix |
|---------|-----|
| `GOOGLE_API_KEY` error | Check `.env` file has a valid key |
| Camera not found | Set `DEMO_MODE=true` or check `CAMERA_INDEX` |
| No audio output | Check `AUDIO_DEVICE_INDEX` or set `DEMO_MODE=true` |
| Port 8000 in use | Kill existing process or change `BACKEND_PORT` |
| Frontend blank page | Run `npm install` in `frontend/` directory |
| Quota exceeded | Switch to `gemini-2.5-flash-lite` or wait until midnight |
