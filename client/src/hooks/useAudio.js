import { useState, useEffect, useRef, useCallback } from 'react';

// Pre-load audio elements
const audioFiles = {
  theme: '/sounds/naruto-theme.mp3',
  win: '/sounds/winner.mp3',
  loss: '/sounds/lost.mp3',
  jutsuActivation: '/sounds/jutsu-activation.mp3',
  shadowClone: '/sounds/shadow-clone-jutsu.mp3',
  rasengan: '/sounds/rasengan-sound.mp3',
  chidori: '/sounds/chidori-sound.mp3',
};

export function useAudio() {
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.5);
  const sounds = useRef({});

  useEffect(() => {
    // Initialize audio elements
    Object.entries(audioFiles).forEach(([key, path]) => {
      const audio = new Audio(path);
      if (['theme', 'win', 'loss'].includes(key)) {
        audio.loop = key === 'theme'; // Only loop the main theme
      }
      sounds.current[key] = audio;
    });

    return () => {
      // Cleanup
      Object.values(sounds.current).forEach(audio => {
        audio.pause();
        audio.src = '';
      });
    };
  }, []);

  // Update volume and mute state
  useEffect(() => {
    Object.entries(sounds.current).forEach(([key, audio]) => {
      // Only apply mute to background/ambient music
      if (['theme', 'win', 'loss'].includes(key)) {
        audio.muted = isMuted;
      } else {
        audio.muted = false; // Never mute SFX manually
      }
      audio.volume = volume;
    });
  }, [isMuted, volume]);

  const toggleMute = useCallback(() => {
    setIsMuted(prev => !prev);
  }, []);

  const changeVolume = useCallback((newVolume) => {
    setVolume(Math.max(0, Math.min(1, newVolume)));
  }, []);

  const playSound = useCallback((key) => {
    const audio = sounds.current[key];
    if (audio) {
      if (['theme', 'win', 'loss'].includes(key)) {
        // Stop other BGMs
        ['theme', 'win', 'loss'].forEach(bgm => {
          if (sounds.current[bgm]) {
            sounds.current[bgm].pause();
            sounds.current[bgm].currentTime = 0;
          }
        });
      } else {
        // Reset sound effect to start so it can overlap/rapid fire
        audio.currentTime = 0;
      }
      
      audio.play().catch(err => console.log('Audio play failed:', err));
    }
  }, []);

  const stopBGM = useCallback(() => {
    ['theme', 'win', 'loss'].forEach(bgm => {
      if (sounds.current[bgm]) {
        sounds.current[bgm].pause();
        sounds.current[bgm].currentTime = 0;
      }
    });
  }, []);

  const forceUnmuteBGM = useCallback(() => {
    // Force unmute BGM tracks so win/loss always audible regardless of toggle state
    ['theme', 'win', 'loss'].forEach(bgm => {
      if (sounds.current[bgm]) {
        sounds.current[bgm].muted = false;
      }
    });
    setIsMuted(false);
  }, []);

  const playTheme = useCallback(() => playSound('theme'), [playSound]);
  const playWin = useCallback(() => playSound('win'), [playSound]);
  const playLoss = useCallback(() => playSound('loss'), [playSound]);
  const playJutsuActivation = useCallback(() => playSound('jutsuActivation'), [playSound]);
  const playShadowClone = useCallback(() => playSound('shadowClone'), [playSound]);
  const playRasengan = useCallback(() => playSound('rasengan'), [playSound]);
  const playChidori = useCallback(() => playSound('chidori'), [playSound]);

  return {
    isMuted,
    volume,
    toggleMute,
    changeVolume,
    playTheme,
    playWin,
    playLoss,
    playJutsuActivation,
    playShadowClone,
    playRasengan,
    playChidori,
    stopBGM,
    forceUnmuteBGM,
  };
}
