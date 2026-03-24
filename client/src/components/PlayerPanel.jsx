import { motion } from 'framer-motion';

/**
 * PlayerPanel — displays HP bar, Chakra bar, and buffs/debuffs for a player.
 */
export default function PlayerPanel({ player, isActive, isMe }) {
  if (!player) return null;

  const hpPercent = (player.hp / player.max_hp) * 100;
  const chakraPercent = (player.chakra / player.max_chakra) * 100;

  const hpColor = hpPercent > 60 ? '#22c55e' : hpPercent > 30 ? '#eab308' : '#ef4444';

  return (
    <motion.div
      className={`glass-card p-4 ${isActive ? 'turn-active' : ''}`}
      layout
      animate={isActive ? { scale: 1.02 } : { scale: 1 }}
      transition={{ type: 'spring', stiffness: 300 }}
    >
      {/* Name + Turn Indicator */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-[var(--color-text-primary)]">
            {player.name} {isMe && '(You)'}
          </span>
          {player.shadow_clone_active && (
            <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded-full">
              👥 Clone
            </span>
          )}
        </div>
        {isActive && (
          <motion.span
            className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-naruto-orange)]/20 
                       text-[var(--color-naruto-orange-light)] font-semibold"
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ repeat: Infinity, duration: 1.5 }}
          >
            ⚔️ ACTIVE
          </motion.span>
        )}
      </div>

      {/* HP Bar */}
      <div className="mb-2">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-[var(--color-text-secondary)]">HP</span>
          <span style={{ color: hpColor }}>{player.hp}/{player.max_hp}</span>
        </div>
        <div className="bar-track">
          <motion.div
            className="bar-fill"
            style={{ backgroundColor: hpColor }}
            animate={{ width: `${hpPercent}%` }}
            transition={{ duration: 0.6, ease: [0.25, 0.8, 0.25, 1] }}
          />
        </div>
      </div>

      {/* Chakra Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-[var(--color-text-secondary)]">Chakra</span>
          <span className="text-[var(--color-chakra-blue)]">{player.chakra}/{player.max_chakra}</span>
        </div>
        <div className="bar-track">
          <motion.div
            className="bar-fill animate-chakra-flow"
            style={{
              background: 'linear-gradient(90deg, #38bdf8, #67e8f9, #38bdf8)',
            }}
            animate={{ width: `${chakraPercent}%` }}
            transition={{ duration: 0.6, ease: [0.25, 0.8, 0.25, 1] }}
          />
        </div>
      </div>

      {/* Buffs & Debuffs */}
      <div className="flex flex-wrap gap-1.5">
        {player.buffs?.map((b, i) => (
          <span key={`buff-${i}`} className="buff-chip positive">
            ✦ {b.name} ({b.duration}t)
          </span>
        ))}
        {player.debuffs?.map((d, i) => (
          <span key={`debuff-${i}`} className="buff-chip negative">
            ✧ {d.name} ({d.duration}t)
          </span>
        ))}
      </div>

      {/* Cooldowns */}
      {player.cooldowns && Object.keys(player.cooldowns).length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {Object.entries(player.cooldowns).map(([name, turns]) => (
            <span
              key={name}
              className="text-[0.6rem] px-1.5 py-0.5 rounded bg-white/5 text-[var(--color-text-muted)]"
            >
              {name}: {turns}t
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
}
