import { useState, useCallback } from 'react';
import useLectureState from '../hooks/useLectureState.js';
import AlertBanner from '../components/AlertBanner.jsx';

/**
 * Student-facing view — optimised for mobile / laptop use in the classroom.
 *
 * Features:
 *  - See current topic and slide
 *  - See any warnings or call-ons directed at them
 *  - Raise hand (sends inject_speech event to backend)
 *  - Minimal, high-contrast, mobile-friendly design
 */
export default function StudentView() {
  const {
    status,
    topic,
    currentSlide,
    speakingText,
    alerts,
    dismissAlert,
    isConnected,
    sendMessage,
  } = useLectureState();

  const [studentId, setStudentId] = useState(
    () => localStorage.getItem('student_id') || ''
  );
  const [studentName, setStudentName] = useState(
    () => localStorage.getItem('student_name') || ''
  );
  const [question, setQuestion] = useState('');
  const [handRaised, setHandRaised] = useState(false);
  const [savedName, setSavedName] = useState(!!localStorage.getItem('student_name'));

  function saveName(e) {
    e.preventDefault();
    if (!studentName.trim()) return;
    localStorage.setItem('student_name', studentName.trim());
    const id = studentId.trim() || `student-${Date.now()}`;
    localStorage.setItem('student_id', id);
    setStudentId(id);
    setSavedName(true);
  }

  const raiseHand = useCallback(() => {
    setHandRaised(true);
    sendMessage({
      type: 'inject_speech',
      text: question.trim() || `${studentName} raised their hand.`,
      student_id: studentId,
    });
    setQuestion('');
    setTimeout(() => setHandRaised(false), 3000);
  }, [sendMessage, question, studentName, studentId]);

  // ── Name entry screen ──────────────────────────────────────────
  if (!savedName) {
    return (
      <div className="min-h-screen bg-surface-900 flex items-center justify-center p-6">
        <form
          onSubmit={saveName}
          className="card max-w-sm w-full flex flex-col gap-4"
          aria-label="Enter your name to join the session"
        >
          <h1 className="text-xl font-bold text-center text-white">
            🎓 Join Session
          </h1>
          <p className="text-sm text-slate-400 text-center">
            Enter your name to follow along.
          </p>
          <input
            type="text"
            placeholder="Your name"
            value={studentName}
            onChange={(e) => setStudentName(e.target.value)}
            required
            autoFocus
            className="bg-surface-700 border border-surface-600 rounded-md px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Your name"
          />
          <input
            type="text"
            placeholder="Student ID (optional)"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            className="bg-surface-700 border border-surface-600 rounded-md px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Student ID (optional)"
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-md py-2 transition-colors"
          >
            Join →
          </button>
        </form>
      </div>
    );
  }

  // ── Main view ──────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-surface-900 flex flex-col">
      <AlertBanner alerts={alerts} onDismiss={dismissAlert} />

      {/* Header */}
      <header className="bg-surface-800 border-b border-surface-700 px-4 py-3">
        <div className="flex items-center justify-between max-w-lg mx-auto">
          <div>
            <p className="text-xs text-slate-500">Logged in as</p>
            <p className="font-semibold text-white">{studentName}</p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isConnected ? 'bg-green-500 pulse-dot' : 'bg-red-500'
              }`}
            />
            <span className="text-xs text-slate-400">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </header>

      <main className="flex-1 p-4 max-w-lg mx-auto w-full flex flex-col gap-4">

        {/* Current lecture info */}
        <div className="card flex flex-col gap-1">
          <p className="text-xs text-slate-400 uppercase tracking-widest">Current Topic</p>
          <p className="font-semibold text-white text-lg leading-snug">
            {topic || (status === 'idle' ? 'Waiting for lecture to start…' : 'Loading…')}
          </p>
          <div className="flex items-center gap-3 mt-1">
            <span
              className={`text-xs font-medium ${
                status === 'active'
                  ? 'text-green-400'
                  : status === 'paused'
                  ? 'text-yellow-400'
                  : 'text-slate-400'
              }`}
            >
              {status === 'active'
                ? '● Live'
                : status === 'paused'
                ? '⏸ Paused'
                : status === 'ended'
                ? '✓ Ended'
                : '○ Not started'}
            </span>
            <span className="text-xs text-slate-500">Slide {currentSlide}</span>
          </div>
        </div>

        {/* Speaking text */}
        {speakingText && (
          <div className="card border-blue-700/60 bg-blue-950/40" aria-live="polite">
            <p className="text-xs text-blue-400 uppercase tracking-widest mb-1">AI is saying</p>
            <p className="text-white leading-relaxed">&ldquo;{speakingText}&rdquo;</p>
          </div>
        )}

        {/* Raise hand / question */}
        <div className="card flex flex-col gap-3">
          <p className="text-xs text-slate-400 uppercase tracking-widest">Ask a Question</p>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Type your question (or just tap Raise Hand)…"
            rows={3}
            className="bg-surface-700 border border-surface-600 rounded-md px-3 py-2 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Your question"
          />
          <button
            onClick={raiseHand}
            disabled={!isConnected || handRaised}
            className={`font-semibold rounded-md py-3 text-base transition-all ${
              handRaised
                ? 'bg-green-700 text-green-200'
                : 'bg-blue-600 hover:bg-blue-500 text-white'
            } disabled:opacity-50`}
            aria-label="Raise hand"
          >
            {handRaised ? '✋ Hand Raised!' : '✋ Raise Hand'}
          </button>
        </div>

        {/* Recent alerts for this student */}
        {alerts.length > 0 && (
          <div className="card border-yellow-700/60 bg-yellow-950/30">
            <p className="text-xs text-yellow-400 uppercase tracking-widest mb-2">Notifications</p>
            <ul className="space-y-1.5">
              {alerts.map((a) => (
                <li key={a.id} className="flex items-center gap-2 text-sm text-yellow-200">
                  <span>{a.type === 'student_warned' ? '⚠️' : '🙋'}</span>
                  <span>{a.message}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Identity reset */}
        <button
          onClick={() => {
            localStorage.removeItem('student_name');
            localStorage.removeItem('student_id');
            setSavedName(false);
            setStudentName('');
            setStudentId('');
          }}
          className="text-xs text-slate-600 hover:text-slate-400 transition-colors text-center mt-2"
        >
          Change name
        </button>
      </main>
    </div>
  );
}
