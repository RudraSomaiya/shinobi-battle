import { motion } from 'framer-motion';

/**
 * TurnIndicator — shows whose turn it is + turn number.
 */
export default function TurnIndicator({ isMyTurn, turnNumber, activePlayerName }) {
  return (
    <motion.div
      className="flex items-center justify-center gap-3 py-2"
      animate={isMyTurn ? { scale: [1, 1.05, 1] } : {}}
      transition={{ repeat: Infinity, duration: 2 }}
    >
      <div
        className={`px-4 py-2 rounded-xl text-sm font-bold tracking-wide
          ${isMyTurn
            ? 'bg-[var(--color-naruto-orange)]/20 text-[var(--color-naruto-orange-light)] border border-[var(--color-naruto-orange)]/30 animate-pulse-glow'
            : 'bg-white/5 text-[var(--color-text-muted)] border border-white/5'
          }`}
      >
        {isMyTurn ? '⚔️ YOUR TURN' : `⏳ ${activePlayerName || 'Opponent'}'s Turn`}
      </div>
      <span className="text-xs text-[var(--color-text-muted)]">Turn #{turnNumber || 1}</span>
    </motion.div>
  );
}
