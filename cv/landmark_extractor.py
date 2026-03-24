"""
Landmark Extractor — MediaPipe hand landmark detection.

Detects two hands and returns normalized landmarks using the Tasks API.
"""

import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class LandmarkExtractor:
    """Extracts hand landmarks using MediaPipe Tasks API."""

    def __init__(self, max_num_hands: int = 2, min_detection_confidence: float = 0.6,
                 min_tracking_confidence: float = 0.5):
        import os
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "hand_landmarker.task")
        
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def extract(self, frame: np.ndarray) -> list | None:
        """
        Extract hand landmarks from a BGR frame.

        Returns:
            List of hand landmarks (each hand has 21 landmarks with x,y,z),
            or None if no hands detected.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = self.detector.detect(mp_image)

        if not results.hand_landmarks:
            return None

        return results.hand_landmarks

    def draw_landmarks(self, frame: np.ndarray, hand_landmarks_list: list) -> np.ndarray:
        """Draw landmarks and connections on the frame for overlay using cv2 directly since Tasks API lacks it."""
        from skeleton_renderer import HAND_CONNECTIONS, _get_color
        annotated = frame.copy()
        h, w = frame.shape[:2]
        
        for hand_landmarks in hand_landmarks_list:
            points = {}
            for idx, lm in enumerate(hand_landmarks):
                # normalize to pixel coordinates
                nx = int(lm.x * w)
                ny = int(lm.y * h)
                points[idx] = (nx, ny)

            # Draw connections
            for connection in HAND_CONNECTIONS:
                idx1, idx2 = connection
                if idx1 in points and idx2 in points:
                    color = _get_color(idx1, idx2)
                    cv2.line(annotated, points[idx1], points[idx2], color, 2)

            # Draw landmarks as circles
            for pt in points.values():
                cv2.circle(annotated, pt, 3, (255, 255, 255), -1)

        return annotated

    def get_bounding_box(self, hand_landmarks, frame_shape: tuple) -> tuple:
        """Get bounding box (x1, y1, x2, y2) for a hand."""
        h, w = frame_shape[:2]
        xs = [lm.x * w for lm in hand_landmarks]
        ys = [lm.y * h for lm in hand_landmarks]
        margin = 20
        return (
            max(0, int(min(xs)) - margin),
            max(0, int(min(ys)) - margin),
            min(w, int(max(xs)) + margin),
            min(h, int(max(ys)) + margin),
        )

    def close(self) -> None:
        self.detector.close()

