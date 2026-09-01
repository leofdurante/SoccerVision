"""Frame sampling honours the requested analysis window.

Broadcast uploads of school matches open with several minutes of intro
package, so analysing from frame 0 analyses title cards and highlight
clips rather than play. These cover the seek behaviour that lets a coach
point the analyser at the passage they care about.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.services.video_processor import VideoProcessor

FPS = 30.0
DURATION_SECONDS = 10


@pytest.fixture(scope="module")
def clip(tmp_path_factory) -> str:
    """A 10-second clip whose every frame is tinted with its own index, so
    a decoded frame can be traced back to its source position."""
    path = tmp_path_factory.mktemp("window") / "clip.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (64, 48))
    for i in range(int(FPS * DURATION_SECONDS)):
        frame = np.full((48, 64, 3), i % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return str(path)


def _timestamps(clip: str, **kwargs) -> list[float]:
    processor = VideoProcessor(clip, processing_fps=5.0)
    return [round(f.timestamp, 3) for f in processor.extract_frames(**kwargs)]


def test_defaults_to_the_whole_video(clip):
    stamps = _timestamps(clip)
    assert stamps[0] == pytest.approx(0.0)
    assert stamps[-1] == pytest.approx(DURATION_SECONDS - 0.2, abs=0.25)


def test_start_seconds_skips_the_intro(clip):
    stamps = _timestamps(clip, start_seconds=4.0)
    assert stamps, "expected frames after seeking"
    assert min(stamps) >= 3.9
    # nothing from before the requested start leaks through
    assert not [s for s in stamps if s < 3.9]


def test_end_seconds_stops_early(clip):
    stamps = _timestamps(clip, end_seconds=3.0)
    assert stamps
    assert max(stamps) <= 3.05


def test_window_is_bounded_at_both_ends(clip):
    stamps = _timestamps(clip, start_seconds=4.0, end_seconds=6.0)
    assert stamps
    assert min(stamps) >= 3.9
    assert max(stamps) <= 6.05


def test_timestamps_stay_absolute_not_window_relative(clip):
    """The frontend lines these up against the <video> element's own clock,
    so a windowed run must not restart its timestamps at zero."""
    stamps = _timestamps(clip, start_seconds=5.0)
    assert min(stamps) >= 4.9, "timestamps were rebased to the window start"


def test_sampling_cadence_is_unaffected_by_the_offset(clip):
    """A start offset must not change the spacing between samples."""
    plain = _timestamps(clip)
    offset = _timestamps(clip, start_seconds=4.0)
    step_plain = round(plain[1] - plain[0], 3)
    step_offset = round(offset[1] - offset[0], 3)
    assert step_offset == pytest.approx(step_plain, abs=0.01)


def test_negative_start_is_clamped(clip):
    assert _timestamps(clip, start_seconds=-5.0) == _timestamps(clip)


def test_window_past_the_end_yields_nothing(clip):
    assert _timestamps(clip, start_seconds=DURATION_SECONDS + 5) == []
