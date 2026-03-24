"""
Inference Pipeline — real-time hand sign classification.

Pipeline: Webcam → MediaPipe → Skeleton Render → CNN → Stability Check → Confirmed Sign
"""

import os
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Also add parent for config
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server"))

from landmark_extractor import LandmarkExtractor
from skeleton_renderer import render_skeleton
from model import NarutoCNN, CLASS_NAMES, NUM_CLASSES
from config_loader import load_config


class SignInference:
    """Real-time hand sign inference with stability confirmation."""

    def __init__(self, model_path: str | None = None, config: dict | None = None):
        self.config = config or load_config()
        cv_cfg = self.config.get("cv", {})
        self.stability_frames = cv_cfg.get("stability_frames", 5)
        self.confidence_threshold = cv_cfg.get("confidence_threshold", 0.70)

        # Model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = NarutoCNN(NUM_CLASSES).to(self.device)

        if model_path and os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            print(f"Model loaded from {model_path}")
        else:
            print("WARNING: No model weights loaded. Using random weights.")

        self.model.eval()

        # Landmark extractor
        self.extractor = LandmarkExtractor()

        # Stability tracking
        self._history: list[str] = []
        self._confirmed_sign: str | None = None

    def process_frame(self, frame: np.ndarray) -> dict:
        """
        Process a single frame through the full pipeline.

        Returns dict with:
            - raw_prediction: str (class name)
            - confidence: float
            - confirmed_sign: str | None (only set when stable)
            - skeleton_image: np.ndarray (128x128)
            - landmarks: list | None
        """
        # 1. Extract landmarks
        landmarks = self.extractor.extract(frame)

        if landmarks is None:
            self._history.clear()
            return {
                "raw_prediction": "unknown",
                "confidence": 0.0,
                "confirmed_sign": None,
                "skeleton_image": np.zeros((128, 128, 3), dtype=np.uint8),
                "landmarks": None,
            }

        # 2. Render skeleton
        skeleton = render_skeleton(landmarks, size=128)

        # 3. Preprocess for CNN
        tensor = self._preprocess(skeleton)

        # 4. Classify
        with torch.no_grad():
            logits = self.model(tensor)
            probs = F.softmax(logits, dim=1)
            confidence, pred_idx = torch.max(probs, dim=1)
            confidence = confidence.item()
            pred_class = CLASS_NAMES[pred_idx.item()]

        # 5. Stability check
        confirmed = None
        if confidence >= self.confidence_threshold:
            self._history.append(pred_class)
            if len(self._history) > self.stability_frames:
                self._history = self._history[-self.stability_frames:]

            if (len(self._history) >= self.stability_frames and
                    all(h == pred_class for h in self._history)):
                confirmed = pred_class
                self._confirmed_sign = confirmed
                self._history.clear()    # Reset after confirmation
        else:
            self._history.clear()

        return {
            "raw_prediction": pred_class,
            "confidence": confidence,
            "confirmed_sign": confirmed,
            "skeleton_image": skeleton,
            "landmarks": landmarks,
        }

    def _preprocess(self, skeleton: np.ndarray) -> torch.Tensor:
        """Convert skeleton image to model input tensor."""
        # BGR → RGB, normalize to [0, 1]
        img = cv2.cvtColor(skeleton, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        # HWC → CHW
        img = np.transpose(img, (2, 0, 1))
        tensor = torch.from_numpy(img).unsqueeze(0).to(self.device)
        return tensor

    def draw_overlay(self, frame: np.ndarray, result: dict,
                     show_landmarks: bool = True,
                     show_bbox: bool = True,
                     show_confidence: bool = True) -> np.ndarray:
        """Draw prediction overlay on the frame."""
        display = frame.copy()

        # Draw landmarks
        if show_landmarks and result["landmarks"]:
            display = self.extractor.draw_landmarks(display, result["landmarks"])

        # Draw bounding boxes
        if show_bbox and result["landmarks"]:
            for hand_lm in result["landmarks"]:
                x1, y1, x2, y2 = self.extractor.get_bounding_box(hand_lm, frame.shape)
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Draw prediction + confidence
        if show_confidence:
            pred = result["raw_prediction"]
            conf = result["confidence"]
            confirmed = result["confirmed_sign"]

            color = (0, 255, 0) if confirmed else (0, 200, 255)
            
            # Line 1: Prediction Label
            label_text = f"Gesture: {pred.upper()}"
            if confirmed:
                label_text = f"LOCKED: {confirmed.upper()}"
                
            # Line 2: Confidence
            conf_text = f"Confidence: {conf:.1%}"

            cv2.putText(display, label_text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX,
                        0.9, color, 2, cv2.LINE_AA)
            cv2.putText(display, conf_text, (15, 70), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (200, 200, 200), 1, cv2.LINE_AA)

        return display

import argparse
import asyncio
import json
import threading
import websockets

# Async WebSocket bridge
_ws_sender_queue = None

async def _ws_client_loop(ws_url: str, player_id: str, room_id: str):
    """Background async loop for sending predictions upwards to the node server."""
    global _ws_sender_queue
    _ws_sender_queue = asyncio.Queue()
    
    while True:
        try:
            print(f"Connecting to Game Server at {ws_url}...")
            async with websockets.connect(ws_url) as ws:
                print("Inference Controller connected to Game Socket!")
                
                # Setup join message
                join_msg = {
                    "type": "PLAYER_JOINED", 
                    "player_id": player_id,
                    "room_id": room_id,
                    "name": f"SensorController_{player_id[:4]}"
                }
                await ws.send(json.dumps(join_msg))

                while True:
                    sign, confidence = await _ws_sender_queue.get()
                    msg = {
                        "type": "SIGN_DETECTED",
                        "player_id": player_id,
                        "sign": sign,
                        "confidence": confidence
                    }
                    try:
                        await ws.send(json.dumps(msg))
                    except Exception as e:
                         print(f"WS Send fail: {e}")
                         break
        except Exception as e:
            print(f"WS Connection error: {e}. Retrying in 3s...")
            await asyncio.sleep(3)


def run_live_demo(model_path: str | None = None, player_id: str | None = None, 
                  ws_url: str = "ws://localhost:8765", room_id: str = "default"):
    """Run live inference demo with webcam."""
    inference = SignInference(model_path=model_path)

    # Boot socket client bridge in a background thread if player_id is present
    if player_id:
        def start_loop():
             loop = asyncio.new_event_split_or_get() if sys.platform != 'win32' else asyncio.new_event_loop()
             asyncio.set_event_loop(loop)
             loop.run_until_complete(_ws_client_loop(ws_url, player_id, room_id))

        t = threading.Thread(target=start_loop, daemon=True)
        t.start()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open webcam")
        return

    print("=== Naruto Battle — Sign Inference Controller ===")
    if player_id:
        print(f"📡 Transmitting as PLAYER ID: {player_id}")
    print("Press 'q' to quit\n")

    show_landmarks = True
    show_bbox = True
    show_confidence = True

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)  # Mirror
        result = inference.process_frame(frame)

        # Draw overlay
        display = inference.draw_overlay(
            frame, result,
            show_landmarks=show_landmarks,
            show_bbox=show_bbox,
            show_confidence=show_confidence,
        )

        # Show skeleton in corner
        skeleton = result["skeleton_image"]
        skeleton_resized = cv2.resize(skeleton, (128, 128))
        display[10:138, display.shape[1] - 138:display.shape[1] - 10] = skeleton_resized

        # Send to socket if confirmed
        if player_id and result["confirmed_sign"] and _ws_sender_queue:
            if result["confirmed_sign"] != "unknown":
                 try:
                     # Non-blocking async queue push from synchronous loop
                     _ws_sender_queue.put_nowait((result["confirmed_sign"], result["confidence"]))
                 except Exception:
                     pass

        cv2.imshow("Naruto Battle - Inference", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("l"):
            show_landmarks = not show_landmarks
        elif key == ord("b"):
            show_bbox = not show_bbox
        elif key == ord("c"):
            show_confidence = not show_confidence

    cap.release()
    cv2.destroyAllWindows()
    inference.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Naruto Battle Sign Inference Interfacer")
    parser.add_argument("--model", type=str, default=None, help="Weights path")
    parser.add_argument("--player", type=str, default=None, help="Player UUID from Game UI to bind controller signals")
    parser.add_argument("--room", type=str, default="default", help="Match Room ID")
    parser.add_argument("--ws_url", type=str, default="ws://localhost:8765", help="Endpoint to websocket controller")
    args = parser.parse_args()

    model_path = args.model
    if model_path is None:
        default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "naruto_cnn.pth")
        if os.path.exists(default):
            model_path = default

    run_live_demo(model_path, player_id=args.player, ws_url=args.ws_url, room_id=args.room)
