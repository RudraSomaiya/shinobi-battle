"""
Skeleton Renderer — draws hand landmarks on a 128x128 black canvas.

Produces the input image for the CNN classifier.
"""

import cv2
import numpy as np

# MediaPipe hand connections (21 landmarks, 0-20)
HAND_CONNECTIONS = frozenset([
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17)
])

# Color palette for different finger groups
COLORS = {
    "thumb": (255, 100, 100),     # Light blue
    "index": (100, 255, 100),     # Green
    "middle": (100, 100, 255),    # Red
    "ring": (255, 255, 100),      # Cyan
    "pinky": (255, 100, 255),     # Magenta
    "palm": (200, 200, 200),      # Gray
}

# Map landmark indices to finger groups
def _get_color(idx1: int, idx2: int) -> tuple:
    """Get color based on which finger the connection belongs to."""
    fingers = {
        "thumb": {1, 2, 3, 4},
        "index": {5, 6, 7, 8},
        "middle": {9, 10, 11, 12},
        "ring": {13, 14, 15, 16},
        "pinky": {17, 18, 19, 20},
    }
    for name, indices in fingers.items():
        if idx1 in indices or idx2 in indices:
            return COLORS[name]
    return COLORS["palm"]


def render_skeleton(hand_landmarks_list: list, size: int = 128) -> np.ndarray:
    """
    Render hand skeleton(s) onto a black canvas.

    Args:
        hand_landmarks_list: List of MediaPipe hand landmarks.
        size: Output image size (square).

    Returns:
        128x128x3 BGR image with skeleton drawn.
    """
    canvas = np.zeros((size, size, 3), dtype=np.uint8)

    if not hand_landmarks_list:
        return canvas

    # Collect all landmarks to compute normalization bounds
    all_points = []
    for hand_landmarks in hand_landmarks_list:
        for lm in hand_landmarks:
            all_points.append((lm.x, lm.y))

    if not all_points:
        return canvas

    xs, ys = zip(*all_points)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Add padding
    pad = 0.1
    range_x = max(max_x - min_x, 0.01)
    range_y = max(max_y - min_y, 0.01)
    min_x -= range_x * pad
    max_x += range_x * pad
    min_y -= range_y * pad
    max_y += range_y * pad
    range_x = max_x - min_x
    range_y = max_y - min_y

    # Keep aspect ratio
    max_range = max(range_x, range_y)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    min_x = center_x - max_range / 2
    max_x = center_x + max_range / 2
    min_y = center_y - max_range / 2
    max_y = center_y + max_range / 2

    def normalize(x: float, y: float) -> tuple[int, int]:
        nx = int((x - min_x) / (max_x - min_x) * (size - 1))
        ny = int((y - min_y) / (max_y - min_y) * (size - 1))
        return np.clip(nx, 0, size - 1), np.clip(ny, 0, size - 1)

    # Draw each hand
    for hand_landmarks in hand_landmarks_list:
        points = {}
        for idx, lm in enumerate(hand_landmarks):
            points[idx] = normalize(lm.x, lm.y)

        # Draw connections
        for connection in HAND_CONNECTIONS:
            idx1, idx2 = connection
            if idx1 in points and idx2 in points:
                color = _get_color(idx1, idx2)
                cv2.line(canvas, points[idx1], points[idx2], color, 2)

        # Draw landmarks as circles
        for idx, pt in points.items():
            cv2.circle(canvas, pt, 3, (255, 255, 255), -1)

    return canvas
