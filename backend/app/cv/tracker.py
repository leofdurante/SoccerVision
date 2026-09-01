"""Multi-object tracking via ByteTrack.

Uses Ultralytics' bundled ByteTrack implementation (`bytetrack.yaml`),
which ships inside the `ultralytics` package — no separate service or
extra model download required. Detection and tracking share one
underlying YOLO model instance (tracking calls `model.track(...,
persist=True)` on the same weights the `Detector` uses) so we don't pay
to load the model twice, while still exposing tracking behind its own
small interface per the spec.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from app.cv.detector import CLASS_MAP

logger = logging.getLogger("soccervision.cv.tracker")


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

    def __init__(self, model_path: str, confidence_threshold: float = 0.4):
        self.confidence_threshold = confidence_threshold
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
            tracker="bytetrack.yaml",
            persist=True,
            verbose=False,
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


def build_tracker(model_path: str, confidence_threshold: float) -> Tracker:
    try:
        tracker = ByteTrackTracker(model_path, confidence_threshold)
        tracker._ensure_model()
        return tracker
    except Exception:
        logger.exception("Failed to load YOLO model '%s' — falling back to NullTracker", model_path)
        return NullTracker()
