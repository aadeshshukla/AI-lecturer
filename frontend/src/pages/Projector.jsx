import { useEffect, useRef, useState, useCallback } from 'react';
import useLectureState from '../hooks/useLectureState.js';
import VirtualBoard from '../components/VirtualBoard.jsx';

/**
 * Projector view — fullscreen display meant to be shown on the classroom projector.
 *
 * Layout:
 *   Topic title bar (top)
 *   Virtual whiteboard (main area)
 *   Caption bar: speaking text + slide number (bottom)
 *
 * Press F or double-click to toggle fullscreen.
 */
export default function Projector() {
  const { boardElements, currentSlide, speakingText, topic, status } = useLectureState();

  const containerRef = useRef(null);
  const [boardSize, setBoardSize] = useState({ width: 1280, height: 640 });
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Measure board area
  useEffect(() => {
    function measure() {
      if (!containerRef.current) return;
      const { clientWidth, clientHeight } = containerRef.current;
      setBoardSize({ width: clientWidth, height: clientHeight });
    }
    measure();
    const obs = new ResizeObserver(measure);
    if (containerRef.current) obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  // Fullscreen helpers
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  }, []);

  useEffect(() => {
    function onFsChange() {
      setIsFullscreen(!!document.fullscreenElement);
    }
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'f' || e.key === 'F') toggleFullscreen();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggleFullscreen]);

  const statusColor =
    status === 'active'
      ? 'bg-green-900/60 border-green-700'
      : status === 'paused'
      ? 'bg-yellow-900/60 border-yellow-700'
      : 'bg-slate-800/60 border-slate-700';

  return (
    <div
      className="flex flex-col h-screen bg-black select-none"
      onDoubleClick={toggleFullscreen}
      aria-label="Projector view — double-click or press F for fullscreen"
    >
      {/* Title bar */}
      <div className={`flex items-center justify-between px-8 py-3 border-b ${statusColor}`}>
        <h1 className="text-2xl font-bold text-white tracking-tight truncate">
          {topic || 'AI Autonomous Lecturer'}
        </h1>
        <div className="flex items-center gap-4 shrink-0">
          <span
            className={`text-sm font-medium ${
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
              : '○ Standby'}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleFullscreen();
            }}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            {isFullscreen ? '⊠ Exit' : '⊞ Fullscreen'}
          </button>
        </div>
      </div>

      {/* Board area */}
      <div ref={containerRef} className="flex-1 overflow-hidden">
        <VirtualBoard
          elements={boardElements}
          width={boardSize.width}
          height={boardSize.height}
        />
      </div>

      {/* Caption / footer bar */}
      <div className="flex items-center gap-4 px-8 py-3 bg-slate-900/80 border-t border-slate-800 min-h-[56px]">
        <div className="flex-1 min-w-0">
          {speakingText ? (
            <p
              className="text-white text-lg font-medium leading-snug truncate"
              aria-live="polite"
              aria-label="Current AI speech"
            >
              &ldquo;{speakingText}&rdquo;
            </p>
          ) : (
            <p className="text-slate-600 text-sm italic">No speech</p>
          )}
        </div>
        <div
          className="shrink-0 flex flex-col items-end"
          aria-label={`Slide ${currentSlide}`}
        >
          <span className="text-3xl font-bold text-slate-400 leading-none">
            {currentSlide}
          </span>
          <span className="text-xs text-slate-600 uppercase tracking-widest">Slide</span>
        </div>
      </div>
    </div>
  );
}
