"""Reusable video processing abstraction built on OpenCV (frame I/O)
and ffmpeg (on PATH; used explicitly to transcode the annotated output
into a codec browsers can actually decode).

Frame sampling is configurable via PROCESSING_FPS so a 90-minute match
doesn't require running YOLO on every single frame.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator

import cv2
import numpy as np

logger = logging.getLogger("soccervision.video_processor")

# Longest edge of the annotated MP4. Drawing happens at source resolution
# first so boxes stay aligned, then we downscale for a cheaper encode.
ANNOTATED_MAX_WIDTH = 1280


def downscale_for_output(frame: np.ndarray, max_width: int = ANNOTATED_MAX_WIDTH) -> np.ndarray:
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame
    scale = max_width / width
    return cv2.resize(frame, (max_width, int(round(height * scale))), interpolation=cv2.INTER_AREA)


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

    def extract_frames(
        self,
        start_seconds: float = 0.0,
        end_seconds: float | None = None,
    ) -> Iterator[SampledFrame]:
        """Yield frames sampled at `processing_fps` between `start_seconds`
        and `end_seconds`, regardless of the source's native frame rate.

        Seeking matters for real uploads: a broadcast of a school match
        opens with several minutes of intro package, so analysing from
        frame 0 analyses titles and highlight clips rather than play.
        Timestamps stay absolute (measured from the start of the video),
        so they line up with the `<video>` element's own clock.
        """
        metadata = self.get_metadata()
        step = max(1, round(metadata.fps / self.processing_fps)) if self.processing_fps > 0 else 1

        start_seconds = max(0.0, start_seconds)
        first_index = int(start_seconds * metadata.fps)
        last_index = int(end_seconds * metadata.fps) if end_seconds is not None else None

        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise VideoReadError(f"Could not open video file: {self.video_path}")

        try:
            if first_index > 0:
                # Land on a sampling boundary so the emitted cadence is the
                # same whether or not a start offset was given.
                first_index -= first_index % step
                cap.set(cv2.CAP_PROP_POS_FRAMES, first_index)

            sampled_index = 0
            source_index = first_index
            while True:
                if last_index is not None and source_index > last_index:
                    break
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
        frames: Iterable[np.ndarray],
        fps: float | None = None,
    ) -> Path:
        """Write an annotated video from BGR frames, one at a time.

        Frames are not collected into a list first — a 90-second 1080p
        clip at 5 fps is several gigabytes uncompressed, which is what
        made analysis appear to hang after tracking finished.
        """
        return self.write_frame_stream(output_path, frames, fps=fps)

    def write_frame_stream(
        self,
        output_path: Path,
        frames: Iterable[np.ndarray],
        fps: float | None = None,
    ) -> Path:
        iterator = iter(frames)
        try:
            first = next(iterator)
        except StopIteration as exc:
            raise VideoReadError("No frames to write to output video.") from exc

        first = downscale_for_output(first)
        height, width = first.shape[:2]
        output_fps = fps or self.processing_fps or 5.0

        # OpenCV can only reliably write MPEG-4 Part 2 ("mp4v"/FMP4) here.
        # No browser decodes that, so the annotated video would load as a
        # black frame with a spinner. Write it to a scratch file, then let
        # ffmpeg transcode to H.264 — the codec browsers actually support.
        scratch = output_path.with_name(f"{output_path.stem}__raw.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(scratch), fourcc, output_fps, (width, height))
        if not writer.isOpened():
            raise VideoReadError(f"Could not open video writer for {scratch}")
        try:
            writer.write(first)
            for frame in iterator:
                writer.write(downscale_for_output(frame))
        finally:
            writer.release()

        if not self._transcode_to_h264(scratch, output_path):
            # Better a video only some players can open than none at all.
            scratch.replace(output_path)
        else:
            scratch.unlink(missing_ok=True)

        return output_path

    @staticmethod
    def _transcode_to_h264(source: Path, destination: Path) -> bool:
        """Re-encode `source` to browser-playable H.264 + faststart.

        Returns False (and leaves `destination` alone) if ffmpeg is missing
        or fails, so a transcode problem degrades the output rather than
        failing the whole analysis.
        """
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            logger.warning(
                "ffmpeg not found on PATH; annotated video stays MPEG-4 Part 2 "
                "and will not play in a browser"
            )
            return False

        try:
            result = subprocess.run(
                [
                    ffmpeg, "-y", "-loglevel", "error",
                    "-i", str(source),
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-pix_fmt", "yuv420p",   # required for broad browser support
                    "-movflags", "+faststart",  # moov up front so playback can start early
                    str(destination),
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("ffmpeg transcode of %s failed: %s", source.name, exc)
            return False

        if result.returncode != 0:
            logger.warning(
                "ffmpeg transcode of %s exited %d: %s",
                source.name, result.returncode, result.stderr.strip()[:400],
            )
            return False

        return True
