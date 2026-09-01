"""Generates a short synthetic demo video for local testing/demoing the
pipeline end to end, from Ultralytics' public sample photo of soccer
players (zidane.jpg — the same image Ultralytics uses in their own docs
and tests). A real broadcast match clip will demo far better; this just
guarantees `data/demo_assets/demo_match.mp4` always exists and contains
real, detectable people so YOLO produces genuine (if repetitive)
detections without requiring the developer to source footage first.

Usage: python scripts/generate_demo_video.py
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_IMAGE = REPO_ROOT / "data" / "demo_assets" / "zidane.jpg"
OUTPUT_VIDEO = REPO_ROOT / "data" / "demo_assets" / "demo_match.mp4"

FPS = 25
DURATION_SECONDS = 6
ZOOM_AMPLITUDE = 0.04  # subtle pan/zoom so tracking has some motion to work with


def generate() -> Path:
    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(
            f"{SOURCE_IMAGE} not found. Download it first, e.g.:\n"
            f"  curl -sL -o {SOURCE_IMAGE} https://ultralytics.com/images/zidane.jpg"
        )

    image = cv2.imread(str(SOURCE_IMAGE))
    height, width = image.shape[:2]

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(OUTPUT_VIDEO), fourcc, FPS, (width, height))

    total_frames = FPS * DURATION_SECONDS
    for i in range(total_frames):
        t = i / total_frames
        zoom = 1.0 + ZOOM_AMPLITUDE * np.sin(2 * np.pi * t)
        dx = int(10 * np.sin(2 * np.pi * t * 1.3))
        dy = int(6 * np.cos(2 * np.pi * t * 0.9))

        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), 0, zoom)
        matrix[0, 2] += dx
        matrix[1, 2] += dy
        frame = cv2.warpAffine(image, matrix, (width, height), borderMode=cv2.BORDER_REFLECT)
        writer.write(frame)

    writer.release()
    print(f"Wrote {total_frames} frames ({DURATION_SECONDS}s @ {FPS}fps) to {OUTPUT_VIDEO}")
    return OUTPUT_VIDEO


if __name__ == "__main__":
    generate()
