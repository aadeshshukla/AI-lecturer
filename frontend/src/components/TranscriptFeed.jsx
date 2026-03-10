import { useEffect, useRef } from 'react';

/**
 * Auto-scrolling transcript feed showing AI and student speech.
 *
 * @param {{ transcript: Array, maxLines: number }} props
 *   transcript — array of { id, speaker, text } objects
 *   maxLines   — display only the last N lines (default 50)
 */
export default function TranscriptFeed({ transcript = [], maxLines = 50 }) {
  const bottomRef = useRef(null);

  // Auto-scroll to the newest entry
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  const visible = transcript.slice(-maxLines);

  return (
    <div
      className="h-full overflow-y-auto px-1 space-y-1"
      aria-label="Lecture transcript"
    >
      {visible.length === 0 && (
        <p className="text-xs text-slate-500 italic text-center pt-4">
          Transcript will appear here when the lecture starts…
        </p>
      )}
      {visible.map((line) => (
        <TranscriptLine key={line.id} line={line} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function TranscriptLine({ line }) {
  const isAI = line.speaker === 'AI';
  return (
    <div className={`fade-in flex gap-2 text-xs leading-relaxed`}>
      <span
        className={`shrink-0 font-semibold ${
          isAI ? 'text-accent-blue' : 'text-green-400'
        }`}
      >
        [{line.speaker}]
      </span>
      <span className="text-slate-300 break-words">{line.text}</span>
    </div>
  );
}
