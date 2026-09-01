"""Reusable video processing abstraction built on OpenCV (frame I/O)
and ffmpeg (available on PATH, used implicitly by OpenCV's backend on
most platforms; kept as an explicit dependency per the project spec even
though this module doesn't shell out to it directly today).

Frame sampling is configurable via PROCESSING_FPS so a 90-minute match
doesn't require running YOLO on every single frame.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import cv2
import numpy as np

logger = logging.getLogger("soccervision.video_processor")


@dataclass
class VideoMetadata:
    fps: float
    width: int
    height: int
    duration_seconds: float
    frame_count: int


@dataclass
class SampledFrame:
    index: int  # index within the sampled sequence
    source_frame_index: int  # index in the original video
    timestamp: float  # seconds into the video
    image: np.ndarray


class VideoReadError(RuntimeError):
    pass


class VideoProcessor:
    """Wraps a single video file: metadata, frame sampling, and writing
    an annotated output video."""

    def __init__(self, video_path: Path, processing_fps: float = 5.0):
        self.video_path = Path(video_path)
        self.processing_fps = processing_fps
        self._metadata: VideoMetadata | None = None

    def get_metadata(self) -> VideoMetadata:
        if self._metadata is not None:
            return self._metadata

        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise VideoReadError(f"Could not open video file: {self.video_path}")
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if fps <= 0 or width <= 0 or height <= 0:
                raise VideoReadError(
                    f"Video appears unreadable or uses an unsupported codec: {self.video_path}"
                )

            duration = frame_count / fps if fps else 0.0
            self._metadata = VideoMetadata(
                fps=fps,
                width=width,
                height=height,
                duration_seconds=duration,
                frame_count=frame_count,
            )
            return self._metadata
        finally:
            cap.release()

    def extract_frames(self) -> Iterator[SampledFrame]:
        """Yield frames sampled at `processing_fps`, evenly spaced through
        the source video regardless of its native frame rate."""
        metadata = self.get_metadata()
        step = max(1, round(metadata.fps / self.processing_fps)) if self.processing_fps > 0 else 1

        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise VideoReadError(f"Could not open video file: {self.video_path}")

        try:
            sampled_index = 0
            source_index = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if source_index % step == 0:
                    timestamp = source_index / metadata.fps
                    yield SampledFrame(
                        index=sampled_index,
                        source_frame_index=source_index,
                        timestamp=timestamp,
                        image=frame,
                    )
                    sampled_index += 1
                source_index += 1
        finally:
            cap.release()

    def process_frames(
        self, callback: Callable[[SampledFrame], np.ndarray | None]
    ) -> list:
        """Run `callback` over every sampled frame, collecting non-None
        results. Kept generic so callers (detection, tracking, etc.) can
        reuse the same sampling loop."""
        results = []
        for sampled in self.extract_frames():
            result = callback(sampled)
            if result is not None:
                results.append(result)
        return results

    def create_output_video(
        self,
        output_path: Path,
        frames: list[np.ndarray],
        fps: float | None = None,
    ) -> Path:
        """Write an annotated video from a list of BGR frames (as produced
        during the sampled-frame pass)."""
        if not frames:
            raise VideoReadError("No frames to write to output video.")

        height, width = frames[0].shape[:2]
        output_fps = fps or self.processing_fps or 5.0
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, output_fps, (width, height))
        try:
            for frame in frames:
                writer.write(frame)
        finally:
            writer.release()
        return output_path
