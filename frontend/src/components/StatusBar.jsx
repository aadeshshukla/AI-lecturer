/**
 * Top status bar showing connection state, AI status, quota usage.
 *
 * @param {{
 *   status: string,
 *   isConnected: boolean,
 *   geminiThinking: boolean,
 *   quotaUsed: number,
 *   quotaRemaining: number,
 *   speakingText: string
 * }} props
 */
export default function StatusBar({
  status = 'idle',
  isConnected = false,
  geminiThinking = false,
  quotaUsed = 0,
  quotaRemaining = 250,
  speakingText = '',
}) {
  const limit = quotaUsed + quotaRemaining;
  const pct = limit > 0 ? Math.round((quotaUsed / limit) * 100) : 0;

  const aiLabel = geminiThinking
    ? 'Thinking…'
    : speakingText
    ? 'Speaking…'
    : status === 'active'
    ? 'Active'
    : status === 'paused'
    ? 'Paused'
    : status === 'ended'
    ? 'Ended'
    : 'Idle';

  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-surface-800 border-b border-surface-700 text-sm flex-wrap">
      {/* WebSocket connection */}
      <div className="flex items-center gap-1.5" title="Backend connection">
        <span
          className={`inline-block w-2.5 h-2.5 rounded-full ${
            isConnected ? 'bg-green-500 pulse-dot' : 'bg-red-500'
          }`}
        />
        <span className="text-slate-400 text-xs">
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      <span className="text-slate-600 hidden sm:inline">|</span>

      {/* AI status */}
      <div className="flex items-center gap-1.5">
        {geminiThinking && <span className="spinner" aria-hidden="true" />}
        <span
          className={`font-medium ${
            geminiThinking
              ? 'text-blue-400'
              : speakingText
              ? 'text-green-400'
              : 'text-slate-300'
          }`}
        >
          AI: {aiLabel}
        </span>
      </div>

      {/* Speaking preview */}
      {speakingText && (
        <>
          <span className="text-slate-600 hidden sm:inline">|</span>
          <p
            className="text-slate-400 text-xs italic max-w-xs truncate"
            title={speakingText}
            aria-label="Current AI speech"
          >
            &ldquo;{speakingText}&rdquo;
          </p>
        </>
      )}

      {/* Spacer */}
      <div className="ml-auto flex items-center gap-3">
        {/* Quota */}
        <div
          className="flex items-center gap-2"
          aria-label={`API quota: ${quotaUsed} of ${limit} calls used`}
        >
          <span className="text-xs text-slate-400 whitespace-nowrap">
            {quotaUsed}/{limit} calls
          </span>
          <div className="quota-bar w-20 hidden sm:block">
            <div
              className={`quota-bar-fill ${
                pct >= 80 ? 'bg-red-500' : pct >= 60 ? 'bg-yellow-500' : 'bg-blue-500'
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
