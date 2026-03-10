/**
 * Responsive grid of student cards showing presence and attention state.
 *
 * @param {{ students: Array }} props
 *   students — array of student objects from the API / live state
 */
export default function AttendanceGrid({ students = [] }) {
  if (students.length === 0) {
    return (
      <p className="text-sm text-slate-500 text-center py-6">
        No students registered yet.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-2">
      {students.map((student) => (
        <StudentCard key={student.id} student={student} />
      ))}
    </div>
  );
}

function StudentCard({ student }) {
  const score = student.attention_score ?? 1;
  const present = student.is_present;

  const attentionColor =
    score >= 0.7 ? 'bg-green-500' : score >= 0.3 ? 'bg-yellow-500' : 'bg-red-500';

  const presenceLabel = present ? 'Present' : 'Absent';
  const presenceDot = present ? 'bg-green-500' : 'bg-red-500';

  return (
    <div
      className={`card flex flex-col gap-1.5 p-2 ${
        student.warning_count > 0 ? 'border-yellow-600/60' : ''
      }`}
      aria-label={`${student.name} — ${presenceLabel}`}
    >
      {/* Avatar + name row */}
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-sm font-semibold text-slate-300 shrink-0 overflow-hidden">
          {student.photo_path ? (
            <img
              src={`/${student.photo_path}`}
              alt={student.name}
              className="w-full h-full object-cover"
            />
          ) : (
            student.name?.[0]?.toUpperCase() || '?'
          )}
        </div>
        <span className="text-xs font-medium text-slate-200 truncate">{student.name}</span>
      </div>

      {/* Presence badge */}
      <div className="flex items-center gap-1.5">
        <span className={`inline-block w-2 h-2 rounded-full ${presenceDot}`} />
        <span className="text-xs text-slate-400">{presenceLabel}</span>
        {student.warning_count > 0 && (
          <span
            className="ml-auto text-xs bg-yellow-700/50 text-yellow-300 px-1 rounded"
            title="Warning count"
          >
            ⚠ {student.warning_count}
          </span>
        )}
      </div>

      {/* Attention bar */}
      <div className="quota-bar mt-0.5">
        <div
          className={`quota-bar-fill ${attentionColor}`}
          style={{ width: `${Math.round(score * 100)}%` }}
          role="progressbar"
          aria-valuenow={Math.round(score * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Attention score"
        />
      </div>
      <span className="text-xs text-slate-500 text-right">
        {Math.round(score * 100)}% attention
      </span>
    </div>
  );
}
