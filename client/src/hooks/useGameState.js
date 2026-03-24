import { useState, useCallback } from 'react';
import { MessageType } from '../utils/messageTypes';

/**
 * Game state management hook.
 * Processes server messages and maintains local game state.
 */
export function useGameState(playerId) {
  const [gameState, setGameState] = useState(null);
  const [turnResult, setTurnResult] = useState(null);
  const [matchStarted, setMatchStarted] = useState(false);
  const [matchEnded, setMatchEnded] = useState(false);
  const [winner, setWinner] = useState(null);
  const [error, setError] = useState(null);
  const [playersInRoom, setPlayersInRoom] = useState(0);
  const [actionLog, setActionLog] = useState([]);

  const [cloneConfig, setCloneConfig] = useState(null);

  const addToLog = useCallback((entry) => {
    setActionLog((prev) => [entry, ...prev].slice(0, 20));
  }, []);

  const handleMessage = useCallback((data) => {
    switch (data.type) {
      case MessageType.PLAYER_JOINED:
        setPlayersInRoom(data.players_count);
        addToLog({ type: 'info', text: `${data.name} joined the room` });
        break;

      case MessageType.MATCH_START:
        setMatchStarted(true);
        addToLog({ type: 'info', text: 'Match started!' });
        break;

      case MessageType.GAME_STATE_UPDATE:
        setGameState(data.state);
        if (data.config) {
          setCloneConfig(data.config);
        }
        setError(null);
        break;

      case MessageType.TURN_RESULT: {
        const result = data.result;
        setTurnResult(result);
        
        // Build log entry
        let logText = '';
        if (result.action === 'jutsu') {
          logText = result.missed
            ? `${result.jutsu_name} MISSED!`
            : `${result.jutsu_name} hit! ${result.details?.damage_dealt || 0} damage`;
        } else if (result.action === 'focus') {
          logText = `Focus: +${result.chakra_gained} chakra`;
        } else if (result.action === 'shadow_clone') {
          logText = `Shadow Clone! (-${result.chakra_cost} chakra)`;
        } else if (result.action === 'failed_sequence') {
          logText = result.error;
        } else if (result.action === 'cooldown_blocked') {
          logText = result.error;
        }

        if (logText) {
          addToLog({
            type: result.success ? 'success' : 'error',
            text: logText,
            player_id: result.player_id,
          });
        }

        // Auto-clear turn result after delay
        setTimeout(() => setTurnResult(null), 3000);
        break;
      }

      case MessageType.ACTION_ERROR:
        setError(data.error);
        addToLog({ type: 'error', text: data.error });
        setTimeout(() => setError(null), 3000);
        break;

      case MessageType.MATCH_END:
        setMatchEnded(true);
        setWinner(data.winner);
        addToLog({
          type: 'info',
          text: data.winner === playerId ? '🎉 You WIN!' : '💀 You LOST!',
        });
        break;

      default:
        break;
    }
  }, [playerId, addToLog]);

  const isMyTurn = gameState?.active_player_id === playerId;

  const myState = gameState?.players?.find((p) => p.player_id === playerId);
  const opponentState = gameState?.players?.find((p) => p.player_id !== playerId);

  return {
    gameState,
    turnResult,
    matchStarted,
    matchEnded,
    winner,
    error,
    playersInRoom,
    actionLog,
    isMyTurn,
    myState,
    opponentState,
    handleMessage,
    cloneConfig,
  };
}
