import { useEffect, useCallback, useRef, useState } from 'react';
import useLectureState from '../hooks/useLectureState.js';
import useStudents from '../hooks/useStudents.js';
import StatusBar from '../components/StatusBar.jsx';
import LectureControls from '../components/LectureControls.jsx';
import VirtualBoard from '../components/VirtualBoard.jsx';
import AttendanceGrid from '../components/AttendanceGrid.jsx';
import TranscriptFeed from '../components/TranscriptFeed.jsx';
import AlertBanner from '../components/AlertBanner.jsx';

/**
 * Instructor Dashboard — primary control panel for the lecture.
 *
 * Layout:
 *   StatusBar (full width)
 *   Left column:  LectureControls + AttendanceGrid + KnowledgeUpload
 *   Right column: VirtualBoard + TranscriptFeed
 */
export default function Dashboard() {
  const lecture = useLectureState();
  const { students, refetch, addStudent } = useStudents();

  // Merge live state students over the DB list for up-to-date scores
  const mergedStudents = students.map((s) => ({
    ...s,
    ...(lecture.students[s.id] || {}),
  }));

  // Fetch students on mount
  useEffect(() => {
    refetch();
  }, [refetch]);

  // Board size
  const boardRef = useRef(null);
  const [boardSize, setBoardSize] = useState({ width: 700, height: 420 });
  useEffect(() => {
    function measure() {
      if (boardRef.current) {
        const { clientWidth, clientHeight } = boardRef.current;
        setBoardSize({ width: clientWidth, height: Math.max(clientHeight, 300) });
      }
    }
    measure();
    const obs = new ResizeObserver(measure);
    if (boardRef.current) obs.observe(boardRef.current);
    return () => obs.disconnect();
  }, []);

  // API helpers
  async function handleStart(params) {
    const res = await fetch('/api/lecture/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || 'Failed to start lecture');
    }
  }

  async function handlePause() {
    await fetch('/api/lecture/pause', { method: 'POST' });
  }

  async function handleResume() {
    await fetch('/api/lecture/resume', { method: 'POST' });
  }

  async function handleEnd() {
    await fetch('/api/lecture/end', { method: 'POST' });
  }

  // Student add form
  const [addingStudent, setAddingStudent] = useState(false);
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPhoto, setNewPhoto] = useState(null);
  const [addError, setAddError] = useState('');

  async function handleAddStudent(e) {
    e.preventDefault();
    setAddError('');
    const fd = new FormData();
    fd.append('name', newName);
    fd.append('email', newEmail);
    if (newPhoto) fd.append('photo', newPhoto);
    try {
      await addStudent(fd);
      setNewName('');
      setNewEmail('');
      setNewPhoto(null);
      setAddingStudent(false);
    } catch (err) {
      setAddError(err.message);
    }
  }

  // Knowledge upload
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');

  async function handleKnowledgeUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg('');
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('/api/knowledge/upload', { method: 'POST', body: fd });
      const data = await res.json();
      setUploadMsg(res.ok ? `✓ Ingested: ${data.filename}` : data.detail || 'Upload failed');
    } catch {
      setUploadMsg('Upload failed');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }

  return (
    <>
      <AlertBanner alerts={lecture.alerts} onDismiss={lecture.dismissAlert} />

      {/* Status bar */}
      <StatusBar
        status={lecture.status}
        isConnected={lecture.isConnected}
        geminiThinking={lecture.geminiThinking}
        quotaUsed={lecture.quotaUsed}
        quotaRemaining={lecture.quotaRemaining}
        speakingText={lecture.speakingText}
      />

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-3 p-4 h-[calc(100vh-112px)] overflow-hidden">

        {/* LEFT COLUMN */}
        <div className="flex flex-col gap-3 overflow-y-auto pr-1">

          {/* Lecture controls */}
          <section className="card">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">
              Lecture Controls
            </h2>
            <LectureControls
              status={lecture.status}
              onStart={handleStart}
              onPause={handlePause}
              onResume={handleResume}
              onEnd={handleEnd}
            />
          </section>

          {/* Knowledge base upload */}
          <section className="card">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">
              Knowledge Base
            </h2>
            <label
              className={`flex items-center gap-2 cursor-pointer text-sm text-slate-300 hover:text-white transition-colors ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
            >
              <span className="bg-surface-700 border border-surface-600 rounded px-3 py-1.5 text-xs">
                {uploading ? 'Uploading…' : '📎 Upload Document'}
              </span>
              <input
                type="file"
                accept=".pdf,.txt,.md,.docx"
                className="hidden"
                onChange={handleKnowledgeUpload}
                disabled={uploading}
                aria-label="Upload knowledge base document"
              />
            </label>
            {uploadMsg && (
              <p className="text-xs mt-1 text-slate-400">{uploadMsg}</p>
            )}
          </section>

          {/* Attendance grid */}
          <section className="card flex-1">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
                Students ({mergedStudents.length})
              </h2>
              <button
                onClick={() => setAddingStudent((v) => !v)}
                className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                aria-expanded={addingStudent}
              >
                {addingStudent ? '✕ Cancel' : '+ Add'}
              </button>
            </div>

            {addingStudent && (
              <form onSubmit={handleAddStudent} className="mb-3 flex flex-col gap-2">
                <input
                  type="text"
                  placeholder="Name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  required
                  className="bg-surface-700 border border-surface-600 rounded px-2 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <input
                  type="email"
                  placeholder="Email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  required
                  className="bg-surface-700 border border-surface-600 rounded px-2 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <label className="text-xs text-slate-400 flex flex-col gap-1">
                  Photo (optional)
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setNewPhoto(e.target.files?.[0] || null)}
                    className="text-xs text-slate-300"
                    aria-label="Student photo upload"
                  />
                </label>
                {addError && <p className="text-xs text-red-400">{addError}</p>}
                <button
                  type="submit"
                  className="bg-blue-600 hover:bg-blue-500 text-white text-xs rounded py-1.5 transition-colors"
                >
                  Add Student
                </button>
              </form>
            )}

            <AttendanceGrid students={mergedStudents} />
          </section>
        </div>

        {/* RIGHT COLUMN */}
        <div className="flex flex-col gap-3 min-h-0 overflow-hidden">

          {/* Virtual board */}
          <section className="card flex-[2] min-h-0 flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
                Virtual Board
              </h2>
              <span className="text-xs text-slate-500">
                Slide {lecture.currentSlide}
              </span>
            </div>
            <div ref={boardRef} className="flex-1 min-h-0 rounded-lg overflow-hidden">
              <VirtualBoard
                elements={lecture.boardElements}
                width={boardSize.width}
                height={boardSize.height}
              />
            </div>
          </section>

          {/* Transcript */}
          <section className="card flex-1 min-h-0 flex flex-col">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">
              Live Transcript
            </h2>
            <div className="flex-1 min-h-0 overflow-hidden">
              <TranscriptFeed transcript={lecture.transcript} />
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
