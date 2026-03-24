import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import PlayerPanel from './PlayerPanel';
import CameraFeed from './CameraFeed';
import SignBuffer from './SignBuffer';
import ActionBanner from './ActionBanner';
import TurnIndicator from './TurnIndicator';
import ActionLog from './ActionLog';
import OverlayToggle from './OverlayToggle';

/**
 * GameBoard — main game layout.
 * Arranges camera feeds, player panels, buffer, and UI elements.
 */
export default function GameBoard({
  myState,
  opponentState,
  isMyTurn,
  gameState,
  turnResult,
  actionLog,
  localStream,
  remoteStream,
  playerId,
  latestLandmarks,
  matchEnded,
  audio,
  winner,
  cloneConfig,
}) {
  const [overlayOptions, setOverlayOptions] = useState({ landmarks: true, boundingBoxes: true, confidence: true });
  const [showGameOver, setShowGameOver] = useState(false);

  const visual = cloneConfig?.visual;
  const offsetX = visual?.offsetX ?? 15;
  const scale = visual?.scale ?? 0.85;
  const opacity = visual?.opacity ?? 0.5;
  const blur = visual?.blur ?? 1;
  const hueRotate = visual?.hue_rotate ?? 180;

  // Delay Game Over Overlay so damage numbers & HP bars finish animating visually
  useEffect(() => {
    if (matchEnded) {
      const t = setTimeout(() => setShowGameOver(true), 1500);
      return () => clearTimeout(t);
    } else {
      setShowGameOver(false);
    }
  }, [matchEnded]);

  // Handle SFX on actions
  useEffect(() => {
    if (!turnResult || !audio) return;
    
    const action = turnResult.action;
    const jutsuName = turnResult.jutsu_name || '';

    if (action === 'shadow_clone') {
      audio.playShadowClone();
    } else if (action === 'jutsu') {
      if (jutsuName === 'Rasengan') audio.playRasengan();
      else if (jutsuName === 'Chidori') audio.playChidori();
      else audio.playJutsuActivation();
    } else if (['focus', 'failed_sequence', 'cooldown_blocked'].includes(action)) {
      audio.playJutsuActivation();
    }
  }, [turnResult, audio]);

  // Win/Loss audio is now handled imperatively in App.jsx onMessage

  const activePlayerName = gameState?.active_player_id === myState?.player_id
    ? myState?.name
    : opponentState?.name;

  return (
    <div className="h-screen w-screen flex flex-col bg-[var(--color-surface)] overflow-hidden relative">
      {/* Action Banner overlay */}
      <ActionBanner turnResult={turnResult} />

      {/* Top bar: Turn Indicator */}
      <div className="flex-shrink-0 px-4 pt-3">
        <TurnIndicator
          isMyTurn={isMyTurn}
          turnNumber={gameState?.turn_number}
          activePlayerName={activePlayerName}
        />
      </div>

      {/* Main Game Area */}
      <div className="flex-1 flex gap-4 p-4 min-h-0">
        
        {/* Center/Main Column: Camera Feeds + Buffer */}
        <div className="flex-1 flex flex-col gap-3 min-h-0 relative">
          {/* Camera feeds side by side with panels beneath them */}
          <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
            {/* My Side */}
            <div className="flex flex-col gap-3 min-h-0 relative">
              <div className="flex-1 min-h-0 relative rounded-2xl overflow-hidden glass-card border border-white/5">
                {myState?.shadow_clone_active && (
                  <div className="absolute top-2 left-2 bg-indigo-500/80 backdrop-blur-sm text-white text-xs px-2 py-1 rounded-full font-semibold shadow-lg z-30">
                    Shadow Clone Active
                  </div>
                )}
                
                <CameraFeed
                  stream={localStream}
                  label={`${myState?.name || 'You'} (You)`}
                  mirrored={true}
                  overlayOptions={overlayOptions}
                  latestLandmarks={latestLandmarks}
                  cutout={myState?.shadow_clone_active}
                  multiClone={myState?.shadow_clone_active}
                />
              </div>
              <PlayerPanel
                player={myState}
                isActive={gameState?.active_player_id === myState?.player_id}
                isMe={true}
              />
            </div>

            {/* Opponent Side */}
            <div className="flex flex-col gap-3 min-h-0 relative">
              <div className="flex-1 min-h-0 relative rounded-2xl overflow-hidden glass-card border border-white/5">
                {opponentState?.shadow_clone_active && (
                  <div className="absolute top-2 left-2 bg-indigo-500/80 backdrop-blur-sm text-white text-xs px-2 py-1 rounded-full font-semibold shadow-lg z-30">
                    Shadow Clone Active
                  </div>
                )}

                <CameraFeed
                  stream={remoteStream}
                  label={opponentState?.name || 'Opponent'}
                  cutout={opponentState?.shadow_clone_active}
                  multiClone={opponentState?.shadow_clone_active}
                />
              </div>
              <PlayerPanel
                player={opponentState}
                isActive={gameState?.active_player_id === opponentState?.player_id}
                isMe={false}
              />
            </div>
          </div>
        </div >

        {/* Right Sidebar: Action Log + Toggles (Takes ~20% space) */}
        <div className="w-80 flex flex-col gap-3 min-h-0">
          <div className="flex-1 min-h-0 overflow-hidden">
            <ActionLog log={actionLog} />
          </div>

          {/* Sign Buffer inside Sidebar */}
          <div className="flex-shrink-0">
            <SignBuffer
              buffer={gameState?.buffer}
              maxLength={6}
              visible={isMyTurn}
            />
          </div>

          <OverlayToggle onToggle={setOverlayOptions} />
        </div>
      </div>

      {/* Match End Overlay */}
      {showGameOver && (
        <motion.div
          className="absolute inset-0 bg-black/85 backdrop-blur-md flex items-center justify-center z-50 px-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
        >
          <motion.div
            className="glass-card max-w-sm w-full p-8 border border-white/10 text-center relative overflow-hidden"
            initial={{ scale: 0.7, opacity: 0, y: 50 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 120, damping: 15, delay: 0.2 }}
          >
            {/* Background Glow particle */}
            <div className={`absolute -inset-20 blur-3xl rounded-full opacity-20 pointer-events-none ${gameState.winner === playerId ? 'bg-amber-400' : 'bg-red-500'}`} />

            <motion.div 
              className="text-7xl mb-5 filter drop-shadow-lg"
              initial={{ scale: 0 }}
              animate={{ scale: [0, 1.2, 1] }}
              transition={{ type: 'spring', delay: 0.5, duration: 0.6 }}
            >
              {gameState.winner === playerId ? '👑' : '💀'}
            </motion.div>

            <motion.h1 
              className={`text-4xl font-black mb-2 tracking-wider uppercase bg-clip-text text-transparent bg-gradient-to-b ${
                gameState.winner === playerId 
                  ? 'from-amber-200 to-yellow-500' 
                  : 'from-red-400 to-red-600'
              }`}
              initial={{ opacity: 0, letterSpacing: '0.4em' }}
              animate={{ opacity: 1, letterSpacing: '0.05em' }}
              transition={{ delay: 0.8, duration: 0.5 }}
            >
              {gameState.winner === playerId ? 'VICTORY' : 'DEFEAT'}
            </motion.h1>

            <motion.p 
              className="text-sm text-[var(--color-text-secondary)] mb-6"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.1 }}
            >
              {gameState.winner === playerId
                ? 'Your jutsu reigns supreme. A true Hokage material!'
                : 'Overconfidence was your weakness. Train harder, shinobi.'}
            </motion.p>

            <motion.div 
              className="flex flex-col gap-3"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.4 }}
            >
              <button
                onClick={() => window.location.reload()}
                className="w-full py-3.5 rounded-xl bg-gradient-to-r from-[var(--color-naruto-orange)] to-[var(--color-naruto-red)]
                           text-white font-bold cursor-pointer hover:shadow-lg hover:shadow-orange-500/40 transition-all active:scale-95"
              >
                Rematch
              </button>
              <button
                onClick={() => window.location.href = '/'}
                className="w-full py-3 text-sm rounded-xl bg-white/5 border border-white/10 text-[var(--color-text-secondary)]
                           font-medium hover:bg-white/10 hover:text-white transition-all active:scale-95"
              >
                Back to Lobby
              </button>
            </motion.div>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
}
