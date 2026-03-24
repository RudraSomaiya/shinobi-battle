import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useWebRTC } from './hooks/useWebRTC';
import { useGameState } from './hooks/useGameState';
import { useMediaPipe } from './hooks/useMediaPipe';
import { useAudio } from './hooks/useAudio';
import { MessageType } from './utils/messageTypes';
import CalibrationScreen from './components/CalibrationScreen';
import GameBoard from './components/GameBoard';
import { motion } from 'framer-motion';

/**
 * Naruto Battle — Main Application
 *
 * Flow: Lobby → Calibration → Game
 */
function App() {
  const [phase, setPhase] = useState('lobby'); // lobby | calibrating | playing
  const [playerId] = useState(() => crypto.randomUUID());
  const [playerName, setPlayerName] = useState('');
  const [roomId, setRoomId] = useState('default');

  // Game state hook
  const {
    gameState, turnResult, matchStarted, matchEnded, winner,
    error, playersInRoom, actionLog, isMyTurn, myState, opponentState,
    handleMessage: handleGameMessage,
    cloneConfig,
  } = useGameState(playerId);

  const [latestCalibrationSign, setLatestCalibrationSign] = useState(null);

  // Audio manager
  const audio = useAudio();

  // WebSocket message handler
  const onMessage = useCallback((data) => {
    if (data.type === 'CALIBRATION_SIGN' && data.player_id === playerId) {
      setLatestCalibrationSign({ sign: data.sign, confidence: data.confidence });
      return;
    }
    // Handle WebRTC signaling
    if ([MessageType.RTC_OFFER, MessageType.RTC_ANSWER, MessageType.RTC_ICE_CANDIDATE].includes(data.type)) {
      handleSignaling(data);
      return;
    }

    // Handle match start → trigger WebRTC
    if (data.type === MessageType.MATCH_START) {
      handleGameMessage(data);
      // Player 1 (first to join) initiates WebRTC
      if (data.players[0].id === playerId) {
        setTimeout(() => createOffer(), 500);
      }
      audio.playTheme();
      setPhase('playing');
      return;
    }

    // Handle match end → play win/loss audio IMPERATIVELY (no React effects)
    if (data.type === MessageType.MATCH_END) {
      handleGameMessage(data);
      audio.forceUnmuteBGM();
      console.log('[Audio] MATCH_END received. winner:', data.winner, 'me:', playerId, 'iWon:', data.winner === playerId);
      if (data.winner === playerId) {
        audio.playWin();
      } else {
        audio.playLoss();
      }
      return;
    }

    handleGameMessage(data);
  }, [playerId, handleGameMessage, audio]);

  // WebSocket
  const { send, connected } = useWebSocket(onMessage);

  // WebRTC
  const {
    localStream, remoteStream, rtcConnected,
    startLocalStream, createOffer, handleSignaling,
  } = useWebRTC(send, playerId, false);

  // Join room
  const joinRoom = async () => {
    if (!playerName.trim()) return;

    await startLocalStream();

    send({
      type: MessageType.PLAYER_JOINED,
      player_id: playerId,
      name: playerName.trim(),
      room_id: roomId,
    });

    setPhase('calibrating');
  };

  const handleCalibrationReady = () => {
    send({
      type: MessageType.PLAYER_READY,
      player_id: playerId,
    });
    // Wait for opponent — game starts when both are ready
    if (matchStarted) {
      setPhase('playing');
    }
  };

  // Auto-transition to playing when match starts during calibration
  useEffect(() => {
    if (matchStarted && phase === 'calibrating') {
      audio.playTheme();
      setPhase('playing');
    }
  }, [matchStarted, phase, audio]);

  const [hiddenVideoEl, setHiddenVideoEl] = useState(null);
  const [latestLandmarks, setLatestLandmarks] = useState([]);

  useEffect(() => {
    if (hiddenVideoEl && localStream) {
      hiddenVideoEl.srcObject = localStream;
    }
  }, [hiddenVideoEl, localStream]);

  // Client-side automated frame landmark processing
  useMediaPipe(hiddenVideoEl, (landmarks) => {
    setLatestLandmarks(landmarks || []);
    if (landmarks && landmarks.length > 0) {
      send({
        type: 'FRAME_LANDMARKS',
        player_id: playerId,
        landmarks: landmarks,
      });
    }
  });

  // ---- Render Strategy ----
  return (
    <>
      {/* Global Audio Controls */}
      <div className="fixed top-4 right-4 z-[100] flex items-center gap-3 bg-black/40 backdrop-blur-md px-4 py-2 rounded-full border border-white/10">
        <button
          onClick={audio.toggleMute}
          className="text-xl hover:scale-110 active:scale-95 transition-transform"
          title={audio.isMuted ? "Unmute" : "Mute"}
        >
          {audio.isMuted ? '🔇' : '🔊'}
        </button>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={audio.volume}
          onChange={(e) => audio.changeVolume(parseFloat(e.target.value))}
          className="w-24 accent-[var(--color-naruto-orange)]"
        />
      </div>

      {/* Hidden tracker for background MediaPipe processing */}
      <video
        ref={setHiddenVideoEl}
        autoPlay
        playsInline
        muted
        className="fixed top-0 left-0 opacity-0 pointer-events-none w-10 h-10 z-[-1]"
      />

      {/* ---- Lobby Screen ---- */}
      {phase === 'lobby' && (
        <div className="min-h-screen bg-[var(--color-surface)] flex items-center justify-center">
          <motion.div
            className="glass-card p-10 max-w-md w-full mx-4"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            {/* Title */}
            <div className="text-center mb-8">
              <h1 className="text-4xl font-extrabold tracking-tight mb-2">
                <span className="bg-gradient-to-r from-[var(--color-naruto-orange)] to-[var(--color-naruto-red)] bg-clip-text text-transparent">
                  SHINOBI
                </span>
                <span className="text-[var(--color-text-primary)]"> BATTLE</span>
              </h1>
              <p className="text-sm text-[var(--color-text-secondary)]">
                Two-player hand sign battle arena
              </p>
            </div>

            {/* Connection Status */}
            <div className="flex items-center gap-2 mb-6 justify-center">
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
              <span className="text-xs text-[var(--color-text-muted)]">
                {connected ? 'Server Connected' : 'Connecting...'}
              </span>
            </div>

            {/* Form */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5 uppercase tracking-wide">
                  Shinobi Name
                </label>
                <input
                  type="text"
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && joinRoom()}
                  placeholder="Enter your name..."
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-[var(--color-text-primary)]
                             placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-naruto-orange)]/50
                             transition-all text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5 uppercase tracking-wide">
                  Room ID
                </label>
                <input
                  type="text"
                  value={roomId}
                  onChange={(e) => setRoomId(e.target.value)}
                  placeholder="default"
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-[var(--color-text-primary)]
                             placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-naruto-orange)]/50
                             transition-all text-sm"
                />
              </div>

              <button
                onClick={joinRoom}
                disabled={!connected || !playerName.trim()}
                className={`w-full py-3.5 rounded-xl font-bold text-sm tracking-wide transition-all
                  ${connected && playerName.trim()
                    ? 'bg-gradient-to-r from-[var(--color-naruto-orange)] to-[var(--color-naruto-red)] text-white hover:shadow-lg hover:shadow-orange-500/30 cursor-pointer'
                    : 'bg-white/5 text-[var(--color-text-muted)] cursor-not-allowed'
                  }`}
              >
                ⚔️ JOIN BATTLE
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* ---- Calibration Screen ---- */}
      {phase === 'calibrating' && (
        <div className="relative">
          <CalibrationScreen
            onReady={handleCalibrationReady}
            localStream={localStream}
            latestCalibrationSign={latestCalibrationSign}
          />
          {/* Waiting overlay */}
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
            <div className="glass-card px-6 py-3 text-sm text-[var(--color-text-secondary)] flex items-center gap-2">
              <motion.div
                className="w-2 h-2 rounded-full bg-[var(--color-naruto-orange)]"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ repeat: Infinity, duration: 1 }}
              />
              {playersInRoom >= 2
                ? 'Opponent found! Complete calibration to start.'
                : `Waiting for opponent... (${playersInRoom}/2 players)`}
            </div>
          </div>
        </div>
      )}

      {/* ---- Game Screen ---- */}
      {phase === 'playing' && (
        <GameBoard
          myState={myState}
          opponentState={opponentState}
          isMyTurn={isMyTurn}
          gameState={gameState}
          turnResult={turnResult}
          actionLog={actionLog}
          localStream={localStream}
          remoteStream={remoteStream}
          playerId={playerId}
          latestLandmarks={latestLandmarks}
          matchEnded={matchEnded}
          audio={audio}
          winner={winner}
          cloneConfig={cloneConfig}
        />
      )}
    </>
  );
}

export default App;
