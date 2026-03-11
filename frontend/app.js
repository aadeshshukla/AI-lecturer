/**
 * AI Autonomous Lecturer — Frontend Client
 *
 * Handles:
 *  - WebSocket connection to backend
 *  - Web Speech Synthesis (TTS) for AI voice
 *  - Web Speech Recognition (STT) for student questions
 *  - DOM updates for slides, whiteboard, transcript, students
 */

const WS_URL = `ws://${location.host}/ws`;

// ── State ────────────────────────────────────────────────────────────────────

let ws = null;
let lectureStatus = 'idle';
let currentSlide = 1;
let boardElements = [];
let transcriptLines = [];
let students = {};
let isSpeaking = false;
let sttRecognition = null;
let sttActive = false;
let speechQueue = [];
let speechBusy = false;

// ── WebSocket ────────────────────────────────────────────────────────────────

function connectWS() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log('[WS] Connected');
    addTranscriptLine('system', '✓ Connected to AI Lecturer backend');
  };

  ws.onmessage = (evt) => {
    try {
      const event = JSON.parse(evt.data);
      handleEvent(event);
    } catch (e) {
      console.warn('[WS] Failed to parse message', e);
    }
  };

  ws.onclose = () => {
    console.log('[WS] Disconnected — reconnecting in 3s');
    addTranscriptLine('system', '⚠ Connection lost, reconnecting…');
    setTimeout(connectWS, 3000);
  };

  ws.onerror = (err) => {
    console.error('[WS] Error', err);
  };
}

// ── Event Handler ────────────────────────────────────────────────────────────

function handleEvent(event) {
  const { type, data } = event;

  switch (type) {
    case 'lecture_started':
      lectureStatus = 'active';
      updateStatusUI();
      addTranscriptLine('system', `🎓 Lecture started: ${data.topic}`);
      break;

    case 'lecture_paused':
      lectureStatus = 'paused';
      updateStatusUI();
      addTranscriptLine('system', '⏸ Lecture paused');
      break;

    case 'lecture_resumed':
      lectureStatus = 'active';
      updateStatusUI();
      addTranscriptLine('system', '▶ Lecture resumed');
      break;

    case 'lecture_ended':
      lectureStatus = 'ended';
      updateStatusUI();
      addTranscriptLine('system', '✓ Lecture ended');
      break;

    case 'speaking_start':
      queueSpeech(data.text, data.emotion);
      addTranscriptLine('ai', data.text);
      break;

    case 'speaking_end':
      cancelSpeech();
      break;

    case 'board_write':
      addBoardElement({ type: 'text', content: data.content, style: data.style || 'normal' });
      break;

    case 'board_clear':
      clearBoard();
      break;

    case 'board_draw':
      addBoardElement({ type: 'diagram', diagram_type: data.diagram_type, data: data.data });
      break;

    case 'board_highlight':
      // Visual highlight — handled by projector.html separately
      break;

    case 'slide_advanced':
      currentSlide = data.slide_number;
      updateSlideUI(data);
      break;

    case 'student_warned':
      addTranscriptLine('system', `⚠ Warning issued to student: ${data.reason}`);
      markStudentWarned(data.student_id);
      break;

    case 'student_called':
      addTranscriptLine('system', `📢 Calling on student: "${data.question}"`);
      break;

    case 'student_speech':
      addTranscriptLine('student', `Student: ${data.text}`);
      break;

    case 'attendance_updated':
      addTranscriptLine('system', `📋 Attendance: ${data.count} present`);
      markStudentsPresent(data.present_ids);
      break;

    case 'gemini_thinking':
      updateThinkingIndicator(data.status);
      break;

    case 'class_status_update':
      updateAttentionStats(data);
      break;

    case 'tool_called':
    case 'tool_result':
      // Silent — no UI update needed
      break;

    case 'ask_class':
      addTranscriptLine('system', `❓ ${data.question}`);
      break;

    default:
      console.debug('[WS] Unhandled event type:', type, data);
  }
}

// ── TTS (Web Speech Synthesis) ────────────────────────────────────────────────

function queueSpeech(text, emotion) {
  speechQueue.push({ text, emotion });
  if (!speechBusy) processSpeechQueue();
}

function processSpeechQueue() {
  if (speechQueue.length === 0) {
    speechBusy = false;
    hideSpeakingBar();
    return;
  }
  speechBusy = true;
  const { text, emotion } = speechQueue.shift();
  speakText(text, emotion, processSpeechQueue);
}

function speakText(text, emotion, onEnd) {
  if (!('speechSynthesis' in window)) {
    console.warn('Web Speech Synthesis not supported');
    if (onEnd) onEnd();
    return;
  }

  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);

  // Adjust rate/pitch based on emotion
  switch (emotion) {
    case 'enthusiastic': utter.rate = 1.15; utter.pitch = 1.1; break;
    case 'serious':      utter.rate = 0.9;  utter.pitch = 0.9; break;
    case 'encouraging':  utter.rate = 1.0;  utter.pitch = 1.05; break;
    default:             utter.rate = 1.0;  utter.pitch = 1.0;
  }

  utter.lang = 'en-US';
  isSpeaking = true;
  showSpeakingBar(text);

  utter.onend = () => {
    isSpeaking = false;
    if (onEnd) onEnd();
  };
  utter.onerror = () => {
    isSpeaking = false;
    if (onEnd) onEnd();
  };

  window.speechSynthesis.speak(utter);
}

function cancelSpeech() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  speechQueue = [];
  speechBusy = false;
  isSpeaking = false;
  hideSpeakingBar();
}

// ── STT (Web Speech Recognition) ─────────────────────────────────────────────

function initSTT() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn('Web Speech Recognition not supported in this browser');
    const btn = document.getElementById('stt-btn');
    if (btn) btn.textContent = 'STT not supported';
    return;
  }

  sttRecognition = new SpeechRecognition();
  sttRecognition.lang = 'en-US';
  sttRecognition.interimResults = false;
  sttRecognition.continuous = false;

  sttRecognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    sendStudentSpeech(transcript);
    sttActive = false;
    updateSTTButton();
  };

  sttRecognition.onend = () => {
    sttActive = false;
    updateSTTButton();
  };

  sttRecognition.onerror = (e) => {
    console.warn('[STT] Error:', e.error);
    sttActive = false;
    updateSTTButton();
  };
}

function toggleSTT() {
  if (!sttRecognition) return;
  if (sttActive) {
    sttRecognition.stop();
    sttActive = false;
  } else {
    sttRecognition.start();
    sttActive = true;
  }
  updateSTTButton();
}

function updateSTTButton() {
  const btn = document.getElementById('stt-btn');
  if (!btn) return;
  if (sttActive) {
    btn.classList.add('listening');
    btn.innerHTML = '�� Listening… (click to stop)';
  } else {
    btn.classList.remove('listening');
    btn.innerHTML = '🎤 Ask a Question (STT)';
  }
}

function sendStudentSpeech(text) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ type: 'student_speech', text, student_id: 'student' }));
  addTranscriptLine('student', `You: ${text}`);
}

// ── Camera ────────────────────────────────────────────────────────────────────

async function startCamera() {
  const video = document.getElementById('camera-video');
  if (!video) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = stream;
    video.play();
    const placeholder = document.getElementById('camera-placeholder');
    if (placeholder) placeholder.style.display = 'none';
  } catch (err) {
    console.warn('[Camera] Could not access camera:', err.message);
  }
}

// ── UI Helpers ────────────────────────────────────────────────────────────────

function addTranscriptLine(type, text) {
  const container = document.getElementById('transcript');
  if (!container) return;
  const div = document.createElement('div');
  div.className = `transcript-line ${type}`;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function updateSlideUI(data) {
  const numEl = document.getElementById('slide-number');
  if (numEl) numEl.textContent = `Slide ${data.slide_number}`;

  if (data.title) {
    const titleEl = document.getElementById('slide-title');
    if (titleEl) titleEl.textContent = data.title;
  }
  if (data.content) {
    const contentEl = document.getElementById('slide-content');
    if (contentEl) contentEl.textContent = data.content;
  }
}

function addBoardElement(element) {
  boardElements.push(element);
  renderBoard();
}

function clearBoard() {
  boardElements = [];
  renderBoard();
}

function renderBoard() {
  const container = document.getElementById('board-area');
  if (!container) return;
  container.innerHTML = '';
  boardElements.forEach((el) => {
    const div = document.createElement('div');
    if (el.type === 'diagram') {
      div.className = 'board-item';
      div.textContent = `[${el.diagram_type}] ${JSON.stringify(el.data)}`;
    } else {
      div.className = `board-item ${el.style || 'normal'}`;
      div.textContent = el.content;
    }
    container.appendChild(div);
  });
}

function showSpeakingBar(text) {
  const bar = document.getElementById('speaking-bar');
  if (bar) {
    bar.textContent = `🔊 ${text.substring(0, 100)}${text.length > 100 ? '…' : ''}`;
    bar.classList.add('active');
  }
}

function hideSpeakingBar() {
  const bar = document.getElementById('speaking-bar');
  if (bar) bar.classList.remove('active');
}

function updateThinkingIndicator(status) {
  const el = document.getElementById('thinking-indicator');
  if (!el) return;
  if (status === 'thinking') {
    el.textContent = '🤔 AI is thinking…';
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}

function updateStatusUI() {
  const badge = document.getElementById('status-badge');
  if (badge) {
    badge.className = `status-badge ${lectureStatus}`;
    badge.innerHTML = `<span class="dot ${lectureStatus === 'active' ? 'pulse' : ''}"></span> ${lectureStatus}`;
  }
  // Toggle button visibility
  const startBtn = document.getElementById('start-btn');
  const endBtn = document.getElementById('end-btn');
  const pauseBtn = document.getElementById('pause-btn');
  const resumeBtn = document.getElementById('resume-btn');

  if (startBtn) startBtn.style.display = lectureStatus === 'idle' || lectureStatus === 'ended' ? 'block' : 'none';
  if (endBtn) endBtn.style.display = lectureStatus !== 'idle' && lectureStatus !== 'ended' ? 'block' : 'none';
  if (pauseBtn) pauseBtn.style.display = lectureStatus === 'active' ? 'block' : 'none';
  if (resumeBtn) resumeBtn.style.display = lectureStatus === 'paused' ? 'block' : 'none';
}

function markStudentWarned(studentId) {
  const el = document.getElementById(`student-${studentId}`);
  if (el) el.style.borderLeft = '3px solid #ef4444';
}

function markStudentsPresent(ids) {
  ids.forEach((id) => {
    if (students[id]) students[id].is_present = true;
  });
  renderStudents();
}

function updateAttentionStats(data) {
  const el = document.getElementById('attention-avg');
  if (el) el.textContent = `${Math.round((data.average_attention || 0) * 100)}%`;
}

// ── Student Management ────────────────────────────────────────────────────────

async function loadStudents() {
  try {
    const resp = await fetch('/api/students');
    const list = await resp.json();
    students = {};
    list.forEach((s) => { students[s.id] = s; });
    renderStudents();
  } catch (e) {
    console.warn('[Students] Failed to load:', e);
  }
}

function renderStudents() {
  const container = document.getElementById('students-list');
  if (!container) return;
  container.innerHTML = '';
  Object.values(students).forEach((s) => {
    const div = document.createElement('div');
    div.className = 'student-item';
    div.id = `student-${s.id}`;
    const initials = s.name.split(' ').map((w) => w[0]).join('').substring(0, 2).toUpperCase();
    const attention = Math.round((s.attention_score || 1) * 100);
    const attnColor = attention > 70 ? '#22c55e' : attention > 40 ? '#eab308' : '#ef4444';
    div.innerHTML = `
      <div class="student-avatar">${initials}</div>
      <div class="student-info">
        <div class="student-name">${s.name}</div>
        <div class="student-meta">${s.is_present ? '✓ Present' : 'Away'} · ${s.warning_count} warnings</div>
      </div>
      <div class="attention-bar">
        <div class="attention-fill" style="width:${attention}%;background:${attnColor}"></div>
      </div>
    `;
    container.appendChild(div);
  });
}

async function addStudent(name) {
  if (!name.trim()) return;
  try {
    const resp = await fetch('/api/students', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim() }),
    });
    if (resp.ok) {
      const s = await resp.json();
      students[s.id] = s;
      renderStudents();
    }
  } catch (e) {
    console.warn('[Students] Failed to add:', e);
  }
}

// ── Lecture Controls ──────────────────────────────────────────────────────────

async function startLecture() {
  const topic = document.getElementById('topic')?.value?.trim();
  const duration = parseInt(document.getElementById('duration')?.value || '45');
  const difficulty = document.getElementById('difficulty')?.value || 'intermediate';

  if (!topic) {
    alert('Please enter a lecture topic');
    return;
  }

  try {
    const resp = await fetch('/api/lecture/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, duration_minutes: duration, difficulty }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      alert(`Error: ${err.detail}`);
    }
  } catch (e) {
    alert('Failed to start lecture: ' + e.message);
  }
}

async function endLecture() {
  try {
    await fetch('/api/lecture/end', { method: 'POST' });
  } catch (e) {
    console.warn('[Lecture] End failed:', e);
  }
}

async function pauseLecture() {
  try {
    await fetch('/api/lecture/pause', { method: 'POST' });
  } catch (e) {
    console.warn('[Lecture] Pause failed:', e);
  }
}

async function resumeLecture() {
  try {
    await fetch('/api/lecture/resume', { method: 'POST' });
  } catch (e) {
    console.warn('[Lecture] Resume failed:', e);
  }
}

// ── Poll lecture status ───────────────────────────────────────────────────────

async function pollStatus() {
  try {
    const resp = await fetch('/api/lecture/status');
    if (resp.ok) {
      const data = await resp.json();
      lectureStatus = data.status;
      currentSlide = data.current_slide || 1;
      updateStatusUI();

      const elapsed = document.getElementById('time-elapsed');
      if (elapsed) {
        const m = Math.floor(data.time_elapsed / 60);
        const s = data.time_elapsed % 60;
        elapsed.textContent = `${m}:${String(s).padStart(2, '0')}`;
      }

      const studentCount = document.getElementById('student-count');
      if (studentCount) studentCount.textContent = data.student_count || 0;

      const slideEl = document.getElementById('slide-number');
      if (slideEl) slideEl.textContent = `Slide ${data.current_slide || 1}`;
    }
  } catch (e) {
    // Silently ignore
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  connectWS();
  initSTT();
  loadStudents();
  pollStatus();
  setInterval(pollStatus, 5000);

  // Wire buttons
  const startBtn = document.getElementById('start-btn');
  if (startBtn) startBtn.addEventListener('click', startLecture);

  const endBtn = document.getElementById('end-btn');
  if (endBtn) endBtn.addEventListener('click', endLecture);

  const pauseBtn = document.getElementById('pause-btn');
  if (pauseBtn) pauseBtn.addEventListener('click', pauseLecture);

  const resumeBtn = document.getElementById('resume-btn');
  if (resumeBtn) resumeBtn.addEventListener('click', resumeLecture);

  const sttBtn = document.getElementById('stt-btn');
  if (sttBtn) sttBtn.addEventListener('click', toggleSTT);

  // Add student
  const addStudentBtn = document.getElementById('add-student-btn');
  if (addStudentBtn) {
    addStudentBtn.addEventListener('click', () => {
      const input = document.getElementById('add-student-input');
      if (input) {
        addStudent(input.value);
        input.value = '';
      }
    });
  }

  // Camera (dashboard only)
  const cameraVideo = document.getElementById('camera-video');
  if (cameraVideo) startCamera();
});
