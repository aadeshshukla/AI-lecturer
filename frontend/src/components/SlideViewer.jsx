/**
 * Slide number indicator.
 *
 * @param {{ slideNumber: number, slideContent: string }} props
 */
export default function SlideViewer({ slideNumber = 1, slideContent = '' }) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[80px] select-none">
      <div className="text-6xl font-bold text-slate-600 leading-none">{slideNumber}</div>
      <div className="text-xs text-slate-500 mt-1 uppercase tracking-widest">Slide</div>
      {slideContent && (
        <div className="mt-3 text-sm text-slate-300 text-center max-w-xs">
          {slideContent}
        </div>
      )}
    </div>
  );
}
