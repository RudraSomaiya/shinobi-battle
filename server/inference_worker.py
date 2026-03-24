"""
Server-side Inference Worker
Processes landmarks received from client browsers to yield hand sign predictions using the PyTorch CNN.
"""

import os
import sys
import torch
import torch.nn.functional as F
import numpy as np

# Add CV path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cv"))

from model import NarutoCNN, CLASS_NAMES, NUM_CLASSES
from skeleton_renderer import render_skeleton


class InferenceWorker:
    """Loads weights and provides inference forward pass for raw landmarks array."""

    def __init__(self, model_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = NarutoCNN(NUM_CLASSES).to(self.device)
        
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            print(f"[InferenceWorker] Loaded weights from {model_path}")
        else:
            print(f"[InferenceWorker] WARNING: No weights found at {model_path}")
            
        self.model.eval()
        
        # Stability triggers per player
        self.histories = {} # player_id -> list of predictions

    def process_landmarks(self, landmarks_list: list, player_id: str, stability_frames: int = 4) -> dict:
        """
        Process coordinate landmarks from browser client.
        
        Args:
            landmarks_list: List of hand landmarks where each is a list of {x,y,z} points
            player_id: String uuid
            
        Returns dict with confirmed prediction
        """
        if not landmarks_list:
            if player_id in self.histories:
                self.histories[player_id].clear()
            return {"prediction": "unknown", "confidence": 0.0, "confirmed": None}

        # 1. Adapt landmarks array from JS dict representation to object-like
        # skeleton_renderer expects a list of hand lists, each supporting item iterate with .x, .y property
        adapted_hands = []
        for hand in landmarks_list:
            adapted_pts = []
            for pt in hand:
                 # Standard Dict from JSON
                 class Point:
                     def __init__(self, x, y, z):
                         self.x = x
                         self.y = y
                         self.z = z
                 adapted_pts.append(Point(pt.get('x', 0), pt.get('y', 0), pt.get('z', 0)))
            adapted_hands.append(adapted_pts)

        # 2. Render skeleton
        skeleton = render_skeleton(adapted_hands, size=128)

        # 3. Preprocess for CNN
        # BGR -> RGB, normalization
        img = cv2_preprocess(skeleton)
        tensor = torch.from_numpy(img).unsqueeze(0).to(self.device)

        # 4. Forward pass
        with torch.no_grad():
             outputs = self.model(tensor)
             probs = F.softmax(outputs, dim=1)
             confidence, pred_idx = torch.max(probs, dim=1)
             confidence = confidence.item()
             pred_class = CLASS_NAMES[pred_idx.item()]

        # 5. Time-based Stability buffer (0.8s hold)
        import time
        if player_id not in self.histories:
            self.histories[player_id] = {
                "current_sign": None,
                "start_time": 0.0,
                "last_confirmed": None
            }
            
        state = self.histories[player_id]
        confirmed = None
        
        # We enforce a slightly higher confidence for automated triggers
        if confidence >= 0.75:
            if state["current_sign"] != pred_class:
                # Sign changed ➔ reset timer
                state["current_sign"] = pred_class
                state["start_time"] = time.time()
            else:
                elapsed = time.time() - state["start_time"]
                # Require 0.8 seconds continuous hold to confirm!
                if elapsed >= 0.8:
                    if state["last_confirmed"] != pred_class:
                        confirmed = pred_class
                        state["last_confirmed"] = pred_class
        else:
            state["current_sign"] = None
            state["start_time"] = 0.0
            # We DONT clear last_confirmed here, so dropping your hands and making
            # the same sign again works after safety gap triggers in server buffer.
            # Wait, actually to allow consecutive same sign after buffer clearance we should reset it
            state["last_confirmed"] = None

        return {"prediction": pred_class, "confidence": confidence, "confirmed": confirmed}


def cv2_preprocess(skeleton: np.ndarray) -> np.ndarray:
    """Preprocess image representation (Inference.py replicate)."""
    import cv2
    img = cv2.cvtColor(skeleton, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))
    return img
