import { useEffect, useRef } from 'react';

/**
 * useMediaPipe — runs client-side hand tracking in browser.
 * 
 * @param {HTMLVideoElement} videoElement The video stream element to bind.
 * @param {Function} onLandmarks Callback receiving coordinate arrays.
 */
export function useMediaPipe(videoElement, onLandmarks) {
  const handsRef = useRef(null);
  const animationRef = useRef(null);
  const initializedRef = useRef(false);

  useEffect(() => {
    if (!videoElement) return;
    if (initializedRef.current) return;
    initializedRef.current = true;

    const loadMediaPipe = async () => {
      // Use the global object injected by the CDN <script> tags in index.html
      const Hands = window.Hands;

      if (!Hands) {
        console.error("MediaPipe Hands library not loaded from CDN.");
        return;
      }

      const hands = new Hands({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
      });

      hands.setOptions({
        maxNumHands: 2,
        modelComplexity: 1,
        minDetectionConfidence: 0.60,
        minTrackingConfidence: 0.50,
      });

      hands.onResults((results) => {
        if (!onLandmarks) return;
        
        if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
           onLandmarks(results.multiHandLandmarks);
        } else {
           onLandmarks([]);
        }
      });

      handsRef.current = hands;

      // Start processing loop on the existing WebRTC video stream
      const processFrame = async () => {
        if (videoElement.readyState >= 2 && handsRef.current) {
          try {
            await handsRef.current.send({ image: videoElement });
          } catch (e) {
            // Ignore frame drops
          }
        }
        animationRef.current = requestAnimationFrame(processFrame);
      };

      videoElement.addEventListener('loadeddata', processFrame);
      if (videoElement.readyState >= 2) {
        processFrame();
      }
    };

    loadMediaPipe();

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      if (handsRef.current) handsRef.current.close();
    };
  }, [videoElement, onLandmarks]);

  return { handsInstance: handsRef.current };
}
