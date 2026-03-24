import { useEffect, useRef } from 'react';

/**
 * CameraFeed — renders a WebRTC video stream element, with optional landmark overlay canvas.
 * overlayOptions: { landmarks: bool, boundingBoxes: bool, confidence: bool }
 * latestLandmarks: array of hand landmark arrays from useMediaPipe (only relevant for local feed)
 */
export default function CameraFeed({ stream, label, mirrored = false, overlayOptions, latestLandmarks }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  // Draw overlay whenever landmarks or options change
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;
    const ctx = canvas.getContext('2d');

    const draw = () => {
      // Match canvas size to the rendered video element
      const w = video.offsetWidth;
      const h = video.offsetHeight;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      ctx.clearRect(0, 0, w, h);

      if (!overlayOptions?.landmarks && !overlayOptions?.boundingBoxes) return;
      if (!latestLandmarks || latestLandmarks.length === 0) return;

      // MediaPipe landmarks are 0..1 normalized
      const HAND_CONNECTIONS = [
        [0,1],[1,2],[2,3],[3,4],       // Thumb
        [0,5],[5,6],[6,7],[7,8],       // Index
        [0,9],[9,10],[10,11],[11,12],  // Middle
        [0,13],[13,14],[14,15],[15,16],// Ring
        [0,17],[17,18],[18,19],[19,20],// Pinky
        [5,9],[9,13],[13,17],          // Palm
      ];

      for (const hand of latestLandmarks) {
        if (!hand || hand.length < 21) continue;

        // Scale points to canvas pixels (mirrored feed needs to flip x)
        const pts = hand.map(pt => ({
          x: mirrored ? (1 - pt.x) * w : pt.x * w,
          y: pt.y * h,
        }));

        if (overlayOptions?.landmarks) {
          // Draw connections
          ctx.strokeStyle = 'rgba(251, 146, 60, 0.85)';
          ctx.lineWidth = 2;
          for (const [a, b] of HAND_CONNECTIONS) {
            ctx.beginPath();
            ctx.moveTo(pts[a].x, pts[a].y);
            ctx.lineTo(pts[b].x, pts[b].y);
            ctx.stroke();
          }
          // Draw joints
          for (const pt of pts) {
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(254, 215, 170, 0.9)';
            ctx.fill();
          }
        }

        if (overlayOptions?.boundingBoxes) {
          const xs = pts.map(p => p.x);
          const ys = pts.map(p => p.y);
          const minX = Math.min(...xs) - 10;
          const minY = Math.min(...ys) - 10;
          const bw = Math.max(...xs) - minX + 20;
          const bh = Math.max(...ys) - minY + 20;
          ctx.strokeStyle = 'rgba(251, 146, 60, 0.6)';
          ctx.lineWidth = 2;
          ctx.setLineDash([6, 3]);
          ctx.strokeRect(minX, minY, bw, bh);
          ctx.setLineDash([]);
        }
      }
    };

    // Redraw every animation frame so it tracks live
    let animId;
    const loop = () => {
      draw();
      animId = requestAnimationFrame(loop);
    };
    animId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animId);
  }, [overlayOptions, latestLandmarks, mirrored]);

  return (
    <div className="relative rounded-xl overflow-hidden bg-black/40 border border-white/5 w-full h-full">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover"
        style={{ transform: mirrored ? 'scaleX(-1)' : 'none' }}
      />
      {/* Overlay canvas — sits on top of the video, no pointer events */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
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
