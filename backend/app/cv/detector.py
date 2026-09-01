"""Player/ball/referee detection.

Wraps Ultralytics YOLOv8 (COCO-pretrained `yolov8n.pt` by default — see
.env.example for rationale) behind a small `Detector` interface so the
rest of the app never imports `ultralytics` directly and the model can be
swapped for a soccer-specific fine-tuned checkpoint later without
touching any caller.

COCO has no "referee" class, so referees are detected as generic
`person` just like players; there is no ball-vs-referee-vs-player
ambiguity to resolve there. Downstream (team_classifier) flags a
low-confidence / off-palette shirt color as a best-effort referee signal
— this is called out as a known limitation in the README, not hidden.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import numpy as np

logger = logging.getLogger("soccervision.cv.detector")

# COCO class ids relevant to a soccer broadcast frame.
_COCO_PERSON = 0
_COCO_SPORTS_BALL = 32

CLASS_MAP = {
    _COCO_PERSON: "player",
    _COCO_SPORTS_BALL: "ball",
}


@dataclass
class Detection:
    class_id: int
    class_name: str  # "player" | "ball"
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]
    center: list[float]  # [x, y]

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "center": self.center,
        }


class Detector(Protocol):
    def detect(self, frame: np.ndarray) -> list[Detection]: ...


class YoloDetector:
    """Ultralytics YOLOv8-backed implementation of `Detector`."""

    def __init__(self, model_path: str, confidence_threshold: float = 0.4):
        self.confidence_threshold = confidence_threshold
        self._model = None
        self._model_path = model_path

    def _ensure_model(self):
        if self._model is None:
            from ultralytics import YOLO  # imported lazily: heavy dependency

            logger.info("Loading YOLO model: %s", self._model_path)
            self._model = YOLO(self._model_path)
        return self._model

    def detect(self, frame: np.ndarray) -> list[Detection]:
        model = self._ensure_model()
        results = model.predict(
            frame,
            classes=list(CLASS_MAP.keys()),
            conf=self.confidence_threshold,
            verbose=False,
        )
        detections: list[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                class_id = int(box.cls[0])
                if class_id not in CLASS_MAP:
                    continue
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                detections.append(
                    Detection(
                        class_id=class_id,
                        class_name=CLASS_MAP[class_id],
                        confidence=float(box.conf[0]),
                        bbox=[x1, y1, x2, y2],
                        center=[(x1 + x2) / 2, (y1 + y2) / 2],
                    )
                )
        return detections


class NullDetector:
    """No-op detector used when model loading fails, so the pipeline can
    degrade gracefully instead of crashing the whole job."""

    def detect(self, frame: np.ndarray) -> list[Detection]:
        return []


def build_detector(model_path: str, confidence_threshold: float) -> Detector:
    try:
        detector = YoloDetector(model_path, confidence_threshold)
        detector._ensure_model()  # fail fast, not on first real frame
        return detector
    except Exception:
        logger.exception("Failed to load YOLO model '%s' — falling back to NullDetector", model_path)
        return NullDetector()
