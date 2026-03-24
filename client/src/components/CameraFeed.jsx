import { useEffect, useRef } from 'react';

/**
 * CameraFeed — renders a WebRTC video stream element, with optional landmark overlay canvas.
 * overlayOptions: { landmarks: bool, boundingBoxes: bool, confidence: bool }
 * latestLandmarks: array of hand landmark arrays from useMediaPipe (only relevant for local feed)
 */
export default function CameraFeed({ stream, label, mirrored = false, overlayOptions, latestLandmarks, cutout = false, multiClone = false }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const selfieRef = useRef(null);
  const isProcessing = useRef(false); // ← Prevent memory leak overflow

  // Refs for keeping state latest inside async onResults to avoid stale closures
  const landmarksRef = useRef(latestLandmarks);
  const optionsRef = useRef(overlayOptions);

  useEffect(() => {
    landmarksRef.current = latestLandmarks;
    optionsRef.current = overlayOptions;
  }); // runs on every render

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  // Initialize Selfie Segmentation for cutout effect
  useEffect(() => {
    if (!cutout || !window.SelfieSegmentation) return;

    const selfie = new window.SelfieSegmentation({
      locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/selfie_segmentation/${file}`,
    });
    selfie.setOptions({ modelSelection: 0 }); // 0 = general, 1 = landscape
    selfieRef.current = selfie;

    selfie.onResults((results) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;

      // 1. Create Offscreen cutout to avoid target canvas composite collision
      const offscreen = document.createElement('canvas');
      offscreen.width = w;
      offscreen.height = h;
      const tCtx = offscreen.getContext('2d');

      // Draw mask and intersect it with camera feed
      tCtx.drawImage(results.segmentationMask, 0, 0, w, h);
      tCtx.globalCompositeOperation = 'source-in';
      tCtx.drawImage(results.image, 0, 0, w, h);
      tCtx.globalCompositeOperation = 'source-over';

      // 2. Render cascade to main canvas
      ctx.save();
      ctx.clearRect(0, 0, w, h);

      const drawClone = (offX, offY, scale, alpha) => {
        ctx.save();
        ctx.globalAlpha = alpha;
        // Translate and scale around center
        ctx.translate(w * offX, h * offY);
        ctx.translate(w / 2, h / 2);
        ctx.scale(scale, scale);
        ctx.translate(-w / 2, -h / 2);

        // Draw offscreen cutout
        ctx.drawImage(offscreen, 0, 0, w, h);
        ctx.restore();
      };

      if (multiClone) {
        // 1. Draw original video backmost to serve as background
        ctx.drawImage(results.image, 0, 0, w, h);

        // 2. Draw back row (cascade layout supporting original perspective)
        drawClone(-0.25, -0.05, 0.82, 0.82); 
        drawClone(0.25, -0.05, 0.82, 0.82);  
        
        // 3. Draw inner row
        drawClone(-0.12, -0.02, 0.90, 0.90); 
        drawClone(0.12, -0.02, 0.90, 0.90);  
        
        // 4. Draw main cutout in front
        ctx.drawImage(offscreen, 0, 0, w, h);
      } else {
        // Single cutout
        ctx.drawImage(offscreen, 0, 0, w, h);
      }

      // 3. Draw landmarks overlay on top of cutout (avoiding race conditions)
      const currentOptions = optionsRef.current;
      const currentLandmarks = landmarksRef.current;

      if ((currentOptions?.landmarks || currentOptions?.boundingBoxes) && currentLandmarks?.length > 0) {
        const HAND_CONNECTIONS = [
          [0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[0,9],[9,10],
          [10,11],[11,12],[0,13],[13,14],[14,15],[15,16],[0,17],[17,18],
          [18,19],[19,20],[5,9],[9,13],[13,17]
        ];

        for (const hand of currentLandmarks) {
          if (!hand || hand.length < 21) continue;
          const pts = hand.map(pt => ({
            x: pt.x * w, // CSS scaleX(-1) handles mirroring for the whole canvas
            y: pt.y * h,
          }));

          if (currentOptions?.landmarks) {
            ctx.strokeStyle = 'rgba(251, 146, 60, 0.85)';
            ctx.lineWidth = 2;
            for (const [a, b] of HAND_CONNECTIONS) {
              ctx.beginPath(); ctx.moveTo(pts[a].x, pts[a].y); ctx.lineTo(pts[b].x, pts[b].y); ctx.stroke();
            }
            for (const pt of pts) {
              ctx.beginPath(); ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
              ctx.fillStyle = 'rgba(254, 215, 170, 0.9)'; ctx.fill();
            }
          }
        }
      }

      ctx.restore();
    });

    return () => {
      if (selfieRef.current) selfieRef.current.close();
    };
  }, [cutout]);

  // Draw landmarks overlay
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;
    const ctx = canvas.getContext('2d');

    const draw = () => {
      const w = video.offsetWidth;
      const h = video.offsetHeight;
      if (w === 0 || h === 0) return;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }

      // If NOT using cutout, clear and redraw landmarks
      if (!cutout) {
        ctx.clearRect(0, 0, w, h);
      }

      // Send frame to Selfie Segmentation if active and not already processing
      if (cutout && selfieRef.current && video.readyState >= 2 && !isProcessing.current) {
        isProcessing.current = true;
        selfieRef.current.send({ image: video }).finally(() => {
          isProcessing.current = false;
        });
      }

      if (!overlayOptions?.landmarks && !overlayOptions?.boundingBoxes) return;
      if (!latestLandmarks || latestLandmarks.length === 0) return;

      const HAND_CONNECTIONS = [
        [0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[0,9],[9,10],
        [10,11],[11,12],[0,13],[13,14],[14,15],[15,16],[0,17],[17,18],
        [18,19],[19,20],[5,9],[9,13],[13,17]
      ];

      for (const hand of latestLandmarks) {
        if (!hand || hand.length < 21) continue;
        const pts = hand.map(pt => ({
          x: mirrored ? (1 - pt.x) * w : pt.x * w,
          y: pt.y * h,
        }));

        if (overlayOptions?.landmarks) {
          ctx.strokeStyle = 'rgba(251, 146, 60, 0.85)';
          ctx.lineWidth = 2;
          for (const [a, b] of HAND_CONNECTIONS) {
            ctx.beginPath();
            ctx.moveTo(pts[a].x, pts[a].y);
            ctx.lineTo(pts[b].x, pts[b].y);
            ctx.stroke();
          }
          for (const pt of pts) {
            ctx.beginPath(); ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(254, 215, 170, 0.9)'; ctx.fill();
          }
        }
      }
    };

    let animId;
    const loop = () => { draw(); animId = requestAnimationFrame(loop); };
    animId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animId);
  }, [overlayOptions, latestLandmarks, mirrored, cutout]);

  return (
    <div className="relative rounded-xl overflow-hidden bg-black/40 border border-white/5 w-full h-full">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={`w-full h-full object-cover ${cutout ? 'opacity-0' : 'block'}`}
        style={{ transform: mirrored ? 'scaleX(-1)' : 'none' }}
      />
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ transform: (cutout && mirrored) ? 'scaleX(-1)' : 'none' }}
      />
      {!stream && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className="text-3xl mb-2">📷</div>
            <p className="text-sm text-[var(--color-text-muted)]">Waiting for camera...</p>
          </div>
        </div>
      )}
      {label && (
        <div className="absolute bottom-2 left-2 px-2 py-1 rounded-lg bg-black/60 text-xs font-medium">
          {label}
        </div>
      )}
    </div>
  );
}
