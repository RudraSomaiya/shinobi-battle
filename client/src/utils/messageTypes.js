/**
 * Message protocol types — must match server/message_types.py exactly.
 */
export const MessageType = {
  // Connection / Lobby
  PLAYER_JOINED: 'PLAYER_JOINED',
  PLAYER_READY: 'PLAYER_READY',
  MATCH_START: 'MATCH_START',

  // In-Game Actions
  SIGN_DETECTED: 'SIGN_DETECTED',
  ACTION_SUBMIT: 'ACTION_SUBMIT',
  SHADOW_CLONE_TRIGGER: 'SHADOW_CLONE_TRIGGER',

  // Server → Client
  GAME_STATE_UPDATE: 'GAME_STATE_UPDATE',
  TURN_RESULT: 'TURN_RESULT',
  ACTION_ERROR: 'ACTION_ERROR',
  MATCH_END: 'MATCH_END',

  // WebRTC Signaling
  RTC_OFFER: 'RTC_OFFER',
  RTC_ANSWER: 'RTC_ANSWER',
  RTC_ICE_CANDIDATE: 'RTC_ICE_CANDIDATE',
};
