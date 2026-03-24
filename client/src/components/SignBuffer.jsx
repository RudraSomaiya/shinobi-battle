import { motion, AnimatePresence } from 'framer-motion';
import { SIGN_EMOJIS } from '../utils/constants';

/**
 * SignBuffer — displays the private sign buffer (max 6 slots).
 * Only visible to the active player.
 */
export default function SignBuffer({ buffer, maxLength = 6, visible = false }) {
  const slots = Array.from({ length: maxLength }, (_, i) => buffer?.[i] || null);

  return (
    <div className={`glass-card p-4 transition-all duration-300 ${visible ? 'opacity-100' : 'opacity-0 pointer-events-none select-none'}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">
          Sign Buffer
        </h3>
        <span className="text-xs text-[var(--color-text-muted)]">
          {buffer?.length || 0}/{maxLength}
        </span>
      </div>

      <div className="flex gap-2 justify-center">
        <AnimatePresence mode="popLayout">
          {slots.map((sign, i) => (
            <motion.div
              key={`slot-${i}-${sign || 'empty'}`}
              className={`sign-slot ${sign ? 'filled' : ''}`}
              initial={sign ? { scale: 0.5, opacity: 0 } : false}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.5, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 500, damping: 25 }}
            >
              {sign ? (
                <div className="text-center">
                  <div className="text-lg leading-none mb-0.5">
                    {SIGN_EMOJIS[sign] || '❓'}
                  </div>
                  <div className="text-[0.55rem] leading-none">{sign}</div>
                </div>
              ) : (
                <div className="text-[var(--color-text-muted)] text-lg">·</div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
