/**
 * Game constants
 */

export const SIGN_NAMES = [
  'bird', 'boar', 'dog', 'dragon', 'hare',
  'horse', 'monkey', 'ox', 'rat', 'serpent',
  'tiger', 'ram', 'scrap', 'shadow_clone', 'unknown',
];

export const SIGN_EMOJIS = {
  bird: '🐦', boar: '🐗', dog: '🐕', dragon: '🐉', hare: '🐇',
  horse: '🐴', monkey: '🐒', ox: '🐂', rat: '🐀', serpent: '🐍',
  tiger: '🐅', ram: '🐏', scrap: '❌', shadow_clone: '👥', unknown: '❓',
};

export const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

export const ICE_SERVERS = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
];
