"""Multi-object tracking via ByteTrack.

Uses Ultralytics' ByteTrack implementation with a tuned config
(`trackers/soccer_bytetrack.yaml`) — the shipped defaults assume ~30 fps
broadcast and churn identities badly at the 8 fps this project samples at.
Detection and tracking share one underlying YOLO model instance (tracking
calls `model.track(..., persist=True)` on the same weights the `Detector`
uses) so we don't pay to load the model twice, while still exposing
tracking behind its own small interface per the spec.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

import cv2
import numpy as np

from app.cv.detector import CLASS_MAP

logger = logging.getLogger("soccervision.cv.tracker")

# Tuned for 8 fps sampling of a panning camera; see the file's own header for
# the measurements behind each value.
_TRACKER_CONFIG = Path(__file__).parent / "trackers" / "soccer_bytetrack.yaml"

# Turf in HSV. Wide enough to survive floodlights and shadow, narrow enough to
# exclude the running track, stands and painted graphics.
_GRASS_LOW = (30, 40, 30)
_GRASS_HIGH = (90, 255, 255)


def _playing_surface_mask(frame: np.ndarray) -> np.ndarray:
    """Binary mask of the turf, closed over players standing on it."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, _GRASS_LOW, _GRASS_HIGH)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))


def _feet_on_surface(mask: np.ndarray, bbox: Sequence[float]) -> bool:
    """Is the bottom-centre of this box standing on turf?

    Uses the feet rather than the whole box because a player's body covers
    grass either way — what separates a player from someone on the touchline
    or in the stands is what they are standing on. A detection sitting on the
    scorebug graphic fails this too.
    """
    height, width = mask.shape[:2]
    x1, _, x2, y2 = bbox
    fx = int(np.clip((x1 + x2) / 2, 0, width - 1))
    fy = int(np.clip(y2, 0, height - 1))
    patch = mask[max(0, fy - 5):min(height, fy + 3), max(0, fx - 5):min(width, fx + 6)]
    if patch.size == 0:
        return True  # can't tell — keep it rather than silently drop a player
    return float(patch.mean()) > 60.0


@dataclass
class TrackedObject:
    track_id: int
    class_name: str  # "player" | "ball"
    bbox: list[float]
    center: list[float]
    confidence: float

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "class_name": self.class_name,
            "bbox": self.bbox,
            "center": self.center,
            "confidence": self.confidence,
        }


class Tracker(Protocol):
    def update(self, frame: np.ndarray) -> list[TrackedObject]: ...
    def reset(self) -> None: ...


class ByteTrackTracker:
    """Ultralytics YOLO + built-in ByteTrack implementation of `Tracker`."""

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.45,
        imgsz: int = 1280,
        filter_to_playing_surface: bool = True,
    ):
        self.confidence_threshold = confidence_threshold
        self.imgsz = imgsz
        self.filter_to_playing_surface = filter_to_playing_surface
        self._model_path = model_path
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from ultralytics import YOLO

            logger.info("Loading YOLO model for tracking: %s", self._model_path)
            self._model = YOLO(self._model_path)
        return self._model

    def update(self, frame: np.ndarray) -> list[TrackedObject]:
        model = self._ensure_model()
        results = model.track(
            frame,
            classes=list(CLASS_MAP.keys()),
            conf=self.confidence_threshold,
            # Upscale before inference. In a wide match shot a player is only
            # ~30px tall at 640, which is near what yolov8n can resolve; this
            # roughly doubles how many are found per frame.
            imgsz=self.imgsz,
            tracker=str(_TRACKER_CONFIG),
            persist=True,
            verbose=False,
        )
        surface = (
            _playing_surface_mask(frame) if self.filter_to_playing_surface else None
        )

        tracked: list[TrackedObject] = []
        for result in results:
            boxes = result.boxes
            if boxes is None or boxes.id is None:
                continue
            for box, track_id in zip(boxes, boxes.id):
                class_id = int(box.cls[0])
                if class_id not in CLASS_MAP:
                    continue
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]

                # The ball is legitimately airborne; only people have to be
                # standing on the pitch to count.
                if (
                    surface is not None
                    and CLASS_MAP[class_id] == "player"
                    and not _feet_on_surface(surface, (x1, y1, x2, y2))
                ):
                    continue

                tracked.append(
                    TrackedObject(
                        track_id=int(track_id),
                        class_name=CLASS_MAP[class_id],
                        bbox=[x1, y1, x2, y2],
                        center=[(x1 + x2) / 2, (y1 + y2) / 2],
                        confidence=float(box.conf[0]),
                    )
                )
        return tracked

    def reset(self) -> None:
        """Drop the loaded model so the next `update()` starts a fresh
        ByteTrack state (new video / new analysis job)."""
        self._model = None


class NullTracker:
    def update(self, frame: np.ndarray) -> list[TrackedObject]:
        return []

    def reset(self) -> None:
        pass


def build_tracker(
    model_path: str,
    confidence_threshold: float,
    imgsz: int = 1280,
    filter_to_playing_surface: bool = True,
) -> Tracker:
    try:
        tracker = ByteTrackTracker(
            model_path, confidence_threshold, imgsz, filter_to_playing_surface
        )
        tracker._ensure_model()
        return tracker
    except Exception:
        logger.exception("Failed to load YOLO model '%s' — falling back to NullTracker", model_path)
        return NullTracker()
