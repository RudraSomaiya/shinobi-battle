/**
 * ActionLog — displays the last N game actions in a scrollable list.
 */
export default function ActionLog({ log }) {
  if (!log || log.length === 0) return null;

  const typeColors = {
    success: 'text-green-400',
    error: 'text-red-400',
    info: 'text-blue-400',
  };

  return (
    <div className="glass-card p-3 max-h-[200px] overflow-y-auto">
      <h4 className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-2">
        Action Log
      </h4>
      <div className="space-y-1">
        {log.map((entry, i) => (
          <div
            key={i}
            className={`text-xs ${typeColors[entry.type] || 'text-[var(--color-text-muted)]'}
                       ${i === 0 ? 'animate-slide-up' : ''}`}
          >
            <span className="opacity-60">›</span> {entry.text}
          </div>
        ))}
      </div>
    </div>
  );
}
