import { motion, AnimatePresence } from 'framer-motion';

/**
 * ActionBanner — full-width animated banner showing turn results.
 */
export default function ActionBanner({ turnResult }) {
  if (!turnResult) return null;

  const { action, jutsu_name, missed, success, error, details } = turnResult;

  let title = '';
  let subtitle = '';
  let bgColor = '';
  let icon = '';

  if (action === 'jutsu' && !missed) {
    title = jutsu_name;
    subtitle = `${details?.damage_dealt || 0} damage dealt!`;
    bgColor = 'from-orange-600/90 to-red-600/90';
    icon = '🔥';
  } else if (action === 'jutsu' && missed) {
    title = `${jutsu_name} MISSED!`;
    subtitle = 'Better luck next time';
    bgColor = 'from-gray-600/90 to-gray-800/90';
    icon = '💨';
  } else if (action === 'focus') {
    title = 'FOCUS';
    subtitle = `+${turnResult.chakra_gained} chakra`;
    bgColor = 'from-blue-600/90 to-cyan-600/90';
    icon = '🧘';
  } else if (action === 'shadow_clone') {
    title = 'SHADOW CLONE JUTSU!';
    subtitle = 'Enemy accuracy reduced!';
    bgColor = 'from-purple-600/90 to-violet-600/90';
    icon = '👥';
  } else if (action === 'failed_sequence') {
    title = 'JUTSU FAILED';
    subtitle = error || 'Unknown sequence';
    bgColor = 'from-red-800/90 to-red-900/90';
    icon = '❌';
  } else if (action === 'cooldown_blocked') {
    title = 'ON COOLDOWN';
    subtitle = error;
    bgColor = 'from-yellow-800/90 to-amber-900/90';
    icon = '⏳';
  }

  return (
    <AnimatePresence>
      <motion.div
        className={`fixed top-1/3 left-1/2 -translate-x-1/2 z-50 
                    bg-gradient-to-r ${bgColor} backdrop-blur-lg
                    rounded-2xl px-8 py-5 text-center shadow-2xl
                    border border-white/10 min-w-[320px]`}
        initial={{ y: -80, opacity: 0, scale: 0.8 }}
        animate={{ y: 0, opacity: 1, scale: 1 }}
        exit={{ y: 80, opacity: 0, scale: 0.8 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      >
        <div className="text-3xl mb-1">{icon}</div>
        <h2 className="text-xl font-bold tracking-wide text-white mb-1">{title}</h2>
        <p className="text-sm text-white/70">{subtitle}</p>
      </motion.div>
    </AnimatePresence>
  );
}
