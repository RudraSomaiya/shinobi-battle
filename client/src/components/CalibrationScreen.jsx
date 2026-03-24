import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { SIGN_NAMES, SIGN_EMOJIS } from '../utils/constants';

/**
 * CalibrationScreen — pre-match gesture verification.
 * Shows prediction + confidence so the user can verify their gestures work.
 */
export default function CalibrationScreen({ onReady, localStream, latestCalibrationSign }) {
  const videoRef = useRef(null);
  const [testedSigns, setTestedSigns] = useState(new Set());
  const [currentPrediction, setCurrentPrediction] = useState(null);
  const [currentConfidence, setCurrentConfidence] = useState(0);

  // Signs to verify (exclude unknown)
  const signsToTest = SIGN_NAMES.filter((s) => s !== 'unknown');

  useEffect(() => {
    if (videoRef.current && localStream) {
      videoRef.current.srcObject = localStream;
    }
  }, [localStream]);

  // Hook to watch for incoming calibration sign broadcasts from server
  useEffect(() => {
    if (latestCalibrationSign) {
      const { sign, confidence } = latestCalibrationSign;
      setCurrentPrediction(sign);
      setCurrentConfidence(confidence);
      if (sign !== 'unknown' && confidence > 0.70) {
         setTestedSigns((prev) => new Set([...prev, sign]));
      }
    }
  }, [latestCalibrationSign]);

  const markTested = (sign) => {
    setTestedSigns((prev) => new Set([...prev, sign]));
  };

  const allTested = testedSigns.size >= 5; // Require at least 5

  return (
    <div className="min-h-screen bg-[var(--color-surface)] flex flex-col items-center justify-center p-6">
      <motion.div
        className="glass-card p-8 max-w-2xl w-full"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h2 className="text-2xl font-bold text-center mb-2 text-[var(--color-naruto-orange-light)]">
          ✋ Calibration
        </h2>
        <p className="text-sm text-center text-[var(--color-text-secondary)] mb-6">
          Test your hand signs before the match. Perform each sign in front of the camera.
        </p>

        {/* Camera Preview */}
        <div className="relative rounded-xl overflow-hidden w-full aspect-video bg-black/50 mb-6">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
            style={{ transform: 'scaleX(-1)' }}
          />
          {currentPrediction && (
            <div className="absolute top-3 left-3 px-3 py-1.5 rounded-lg bg-black/70 text-sm font-semibold">
              {SIGN_EMOJIS[currentPrediction]} {currentPrediction}{' '}
              <span className="text-[var(--color-text-muted)]">({(currentConfidence * 100).toFixed(0)}%)</span>
            </div>
          )}
        </div>

        {/* Sign Grid */}
        <div className="grid grid-cols-7 gap-2 mb-6">
          {signsToTest.map((sign) => (
            <button
              key={sign}
              onClick={() => markTested(sign)}
              className={`flex flex-col items-center p-2 rounded-lg text-xs transition-all
                ${testedSigns.has(sign)
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                  : 'bg-white/5 text-[var(--color-text-muted)] border border-white/5 hover:bg-white/10'
                }`}
            >
              <span className="text-lg">{SIGN_EMOJIS[sign]}</span>
              <span className="mt-0.5">{sign}</span>
              {testedSigns.has(sign) && <span className="text-[0.5rem] mt-0.5">✓</span>}
            </button>
          ))}
        </div>

        {/* Ready Button */}
        <div className="text-center">
          <p className="text-xs text-[var(--color-text-muted)] mb-3">
            Tested: {testedSigns.size}/{signsToTest.length} signs
            {!allTested && ' (test at least 5 to continue)'}
          </p>
          <button
            onClick={onReady}
            disabled={!allTested}
            className={`px-8 py-3 rounded-xl font-bold text-sm tracking-wide transition-all
              ${allTested
                ? 'bg-gradient-to-r from-[var(--color-naruto-orange)] to-[var(--color-naruto-red)] text-white hover:shadow-lg hover:shadow-orange-500/30 cursor-pointer'
                : 'bg-white/5 text-[var(--color-text-muted)] cursor-not-allowed'
              }`}
          >
            {allTested ? '⚔️ READY FOR BATTLE' : 'Test more signs...'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
