import { useState } from 'react';

/**
 * OverlayToggle — host controls for CV overlay options.
 */
export default function OverlayToggle({ onToggle }) {
  const [options, setOptions] = useState({
    landmarks: true,
    boundingBoxes: true,
  });

  const toggle = (key) => {
    setOptions((prev) => {
      const updated = { ...prev, [key]: !prev[key] };
      onToggle?.(updated);
      return updated;
    });
  };

  return (
    <div className="glass-card p-3">
      <h4 className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-2">
        CV Overlay
      </h4>
      <div className="flex gap-2">
        {Object.entries(options).map(([key, val]) => (
          <button
            key={key}
            onClick={() => toggle(key)}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all
              ${val
                ? 'bg-[var(--color-naruto-orange)]/20 text-[var(--color-naruto-orange-light)] border border-[var(--color-naruto-orange)]/30'
                : 'bg-white/5 text-[var(--color-text-muted)] border border-white/5'
              }`}
          >
            {key === 'landmarks' ? '🦴' : key === 'boundingBoxes' ? '📦' : '📊'}{' '}
            {key.replace(/([A-Z])/g, ' $1').trim()}
          </button>
        ))}
      </div>
    </div>
  );
}
