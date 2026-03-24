"""
Data Collector — capture training data for the Naruto hand sign CNN.

Controls:
  - Number keys 0-9 + letters a-e: select class (0=bird, 1=boar, ...14=unknown)
  - SPACE: capture current skeleton image for selected class
  - 's': toggle auto-save mode (capture every frame automatically)
  - 'q': quit
"""

import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from landmark_extractor import LandmarkExtractor
from skeleton_renderer import render_skeleton
from model import CLASS_NAMES


def collect_data(output_dir: str = None):
    """Run data collection with webcam."""
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data"
        )

    # Create class directories
    for cls in CLASS_NAMES:
        os.makedirs(os.path.join(output_dir, cls), exist_ok=True)

    extractor = LandmarkExtractor()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Cannot open webcam")
        return

    current_class_idx = 0
    auto_save = False
    frame_count = {cls: len(os.listdir(os.path.join(output_dir, cls)))
                   for cls in CLASS_NAMES}

    # Key mapping for classes
    key_map = {}
    for i in range(10):
        key_map[ord(str(i))] = i
    key_map[ord('a')] = 10
    key_map[ord('b')] = 11
    key_map[ord('c')] = 12
    key_map[ord('d')] = 13
    key_map[ord('e')] = 14

    print("=" * 60)
    print("  NARUTO BATTLE — Data Collector")
    print("=" * 60)
    print("\nClass mapping:")
    for i, cls in enumerate(CLASS_NAMES):
        key = str(i) if i < 10 else chr(ord('a') + i - 10)
        print(f"  [{key}] {cls} ({frame_count[cls]} samples)")
    print(f"\n  [SPACE] Capture frame")
    print(f"  [s]     Toggle auto-save: {'ON' if auto_save else 'OFF'}")
    print(f"  [q]     Quit")
    print("=" * 60)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        landmarks = extractor.extract(frame)

        # Render skeleton
        skeleton = np.zeros((128, 128, 3), dtype=np.uint8)
        if landmarks:
            skeleton = render_skeleton(landmarks, size=128)
            frame = extractor.draw_landmarks(frame, landmarks)

        # UI overlay
        cls_name = CLASS_NAMES[current_class_idx]
        cv2.putText(frame, f"Class: {cls_name} ({frame_count[cls_name]} samples)",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        auto_text = "AUTO-SAVE: ON" if auto_save else "AUTO-SAVE: OFF"
        auto_color = (0, 0, 255) if auto_save else (200, 200, 200)
        cv2.putText(frame, auto_text, (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, auto_color, 2)

        # Show skeleton preview
        skeleton_large = cv2.resize(skeleton, (200, 200))
        y_off = frame.shape[0] - 210
        x_off = frame.shape[1] - 210
        if y_off > 0 and x_off > 0:
            frame[y_off:y_off + 200, x_off:x_off + 200] = skeleton_large

        cv2.imshow("Data Collector", frame)
        cv2.imshow("Skeleton Preview", cv2.resize(skeleton, (256, 256)))

        # Auto-save if active and landmarks detected
        if auto_save and landmarks:
            _save_skeleton(skeleton, output_dir, cls_name, frame_count)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord(" ") and landmarks:
            _save_skeleton(skeleton, output_dir, cls_name, frame_count)
            print(f"  Saved: {cls_name} → {frame_count[cls_name]} total")
        elif key == ord("s"):
            auto_save = not auto_save
            print(f"  Auto-save: {'ON' if auto_save else 'OFF'}")
        elif key in key_map:
            current_class_idx = key_map[key]
            print(f"  Selected class: {CLASS_NAMES[current_class_idx]}")

    cap.release()
    cv2.destroyAllWindows()
    extractor.close()

    print("\nFinal counts:")
    for cls in CLASS_NAMES:
        count = len(os.listdir(os.path.join(output_dir, cls)))
        print(f"  {cls}: {count}")


def _save_skeleton(skeleton: np.ndarray, output_dir: str, cls_name: str,
                   frame_count: dict) -> None:
    """Save a skeleton image to the appropriate class directory."""
    count = frame_count[cls_name]
    filename = f"{cls_name}_{count:05d}.png"
    path = os.path.join(output_dir, cls_name, filename)
    cv2.imwrite(path, skeleton)
    frame_count[cls_name] = count + 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Naruto Battle Data Collector")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory for training data")
    args = parser.parse_args()
    collect_data(args.output)
