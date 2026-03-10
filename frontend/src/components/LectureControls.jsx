import { useState } from 'react';

const DURATION_OPTIONS = [15, 30, 45, 60];
const DIFFICULTY_OPTIONS = ['beginner', 'intermediate', 'advanced'];

/**
 * Lecture control panel — start/pause/resume/end and the start form.
 *
 * @param {{
 *   status: string,
 *   onStart: Function,
 *   onPause: Function,
 *   onResume: Function,
 *   onEnd: Function
 * }} props
 */
export default function LectureControls({ status, onStart, onPause, onResume, onEnd }) {
  const [topic, setTopic] = useState('');
  const [duration, setDuration] = useState(45);
  const [difficulty, setDifficulty] = useState('intermediate');
  const [loading, setLoading] = useState(false);

  async function handleStart(e) {
    e.preventDefault();
    if (!topic.trim()) return;
    setLoading(true);
    try {
      await onStart({ topic: topic.trim(), duration_minutes: duration, difficulty });
    } finally {
      setLoading(false);
    }
  }

  async function handleAction(fn) {
    setLoading(true);
    try {
      await fn();
    } finally {
      setLoading(false);
    }
  }

  // ── Idle / ended → show start form ──────────────────────────────
  if (status === 'idle' || status === 'ended') {
    return (
      <form onSubmit={handleStart} className="flex flex-col gap-3">
        {status === 'ended' && (
          <p className="text-xs text-green-400 font-medium">✓ Session ended.</p>
        )}

        <div className="flex flex-col gap-1">
          <label htmlFor="topic" className="text-xs text-slate-400">
            Topic
          </label>
          <input
            id="topic"
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Introduction to Neural Networks"
            className="bg-surface-700 border border-surface-600 rounded-md px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
            aria-required="true"
          />
        </div>

        <div className="flex gap-2">
          <div className="flex-1 flex flex-col gap-1">
            <label htmlFor="duration" className="text-xs text-slate-400">
              Duration
            </label>
            <select
              id="duration"
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="bg-surface-700 border border-surface-600 rounded-md px-2 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {DURATION_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  {d} min
                </option>
              ))}
            </select>
          </div>

          <div className="flex-1 flex flex-col gap-1">
            <label htmlFor="difficulty" className="text-xs text-slate-400">
              Difficulty
            </label>
            <select
              id="difficulty"
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="bg-surface-700 border border-surface-600 rounded-md px-2 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {DIFFICULTY_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  {d.charAt(0).toUpperCase() + d.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !topic.trim()}
          className="mt-1 w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 disabled:text-blue-400 text-white font-semibold rounded-md py-2 text-sm transition-colors"
          aria-busy={loading}
        >
          {loading ? 'Starting…' : '▶ Start Lecture'}
        </button>
      </form>
    );
  }

  // ── Active ───────────────────────────────────────────────────────
  if (status === 'active') {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-xs text-green-400 font-medium">● Lecture in progress</p>
        <button
          onClick={() => handleAction(onPause)}
          disabled={loading}
          className="w-full bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-white font-semibold rounded-md py-2 text-sm transition-colors"
        >
          ⏸ Pause
        </button>
        <button
          onClick={() => handleAction(onEnd)}
          disabled={loading}
          className="w-full bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white font-semibold rounded-md py-2 text-sm transition-colors"
        >
          ■ End Lecture
        </button>
      </div>
    );
  }

  // ── Paused ───────────────────────────────────────────────────────
  if (status === 'paused') {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-xs text-yellow-400 font-medium">⏸ Lecture paused</p>
        <button
          onClick={() => handleAction(onResume)}
          disabled={loading}
          className="w-full bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white font-semibold rounded-md py-2 text-sm transition-colors"
        >
          ▶ Resume
        </button>
        <button
          onClick={() => handleAction(onEnd)}
          disabled={loading}
          className="w-full bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white font-semibold rounded-md py-2 text-sm transition-colors"
        >
          ■ End Lecture
        </button>
      </div>
    );
  }

  return null;
}
