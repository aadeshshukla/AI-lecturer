import { useEffect, useState } from 'react';

const AUTO_DISMISS_MS = 10_000;

/**
 * Animated alert banner for student warnings and call-ons.
 * Auto-dismisses after AUTO_DISMISS_MS milliseconds.
 *
 * @param {{ alerts: Array, onDismiss: Function }} props
 */
export default function AlertBanner({ alerts = [], onDismiss }) {
  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 flex flex-col gap-2 pointer-events-none px-4 pt-2"
      aria-live="polite"
    >
      {alerts.map((alert) => (
        <AlertItem key={alert.id} alert={alert} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function AlertItem({ alert, onDismiss }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => {
      setVisible(false);
      setTimeout(() => onDismiss?.(alert.id), 350);
    }, AUTO_DISMISS_MS);
    return () => clearTimeout(t);
  }, [alert.id, onDismiss]);

  if (!visible) return null;

  const isWarning = alert.type === 'student_warned';
  const bgClass = isWarning
    ? 'bg-yellow-900/90 border-yellow-600 text-yellow-100'
    : 'bg-blue-900/90 border-blue-600 text-blue-100';

  return (
    <div
      className={`alert-slide-in pointer-events-auto max-w-md mx-auto w-full rounded-lg border px-4 py-3 flex items-center gap-3 shadow-lg ${bgClass}`}
      role="alert"
    >
      <span className="text-xl">{isWarning ? '⚠️' : '🙋'}</span>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm truncate">{alert.studentName}</p>
        <p className="text-xs opacity-80">{alert.message}</p>
      </div>
      <button
        onClick={() => {
          setVisible(false);
          setTimeout(() => onDismiss?.(alert.id), 350);
        }}
        className="text-lg leading-none opacity-60 hover:opacity-100 transition-opacity"
        aria-label="Dismiss alert"
      >
        ×
      </button>
    </div>
  );
}
