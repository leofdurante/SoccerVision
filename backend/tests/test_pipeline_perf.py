from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from app.cv.tracker import ByteTrackTracker
from app.services.analysis_service import _annotate_frame
from app.services.video_processor import VideoProcessor, VideoReadError, downscale_for_output


def test_yolo_runtime_uses_cpu_when_cuda_is_missing(monkeypatch):
    import sys

    import app.cv.runtime as runtime

    class _Torch:
        class cuda:
            @staticmethod
            def is_available():
                return False

    monkeypatch.setitem(sys.modules, "torch", _Torch)
    runtime.reset_yolo_runtime_cache()
    kwargs = runtime.yolo_runtime_kwargs()
    assert kwargs["device"] == "cpu"
    assert "quantize" not in kwargs
    assert "half" not in kwargs
    runtime.reset_yolo_runtime_cache()


def test_yolo_runtime_uses_quantize_not_half_on_cuda(monkeypatch):
    import sys

    import app.cv.runtime as runtime

    class _Torch:
        class cuda:
            @staticmethod
            def is_available():
                return True

    monkeypatch.setitem(sys.modules, "torch", _Torch)
    runtime.reset_yolo_runtime_cache()
    kwargs = runtime.yolo_runtime_kwargs()
    assert kwargs == {"device": 0, "quantize": 16}
    runtime.reset_yolo_runtime_cache()


def test_tracker_reset_keeps_loaded_weights():
    tracker = ByteTrackTracker("yolov8n.pt")
    sentinel = object()
    tracker._model = sentinel
    tracker.reset()
    assert tracker._model is sentinel


def test_tracker_reset_clears_bytetrack_state():
    tracker = ByteTrackTracker("yolov8n.pt")
    inner = MagicMock()
    inner.reset = MagicMock()
    predictor = MagicMock()
    predictor.trackers = [inner]
    predictor.vid_path = ["clip.mp4"]
    model = MagicMock()
    model.predictor = predictor
    tracker._model = model

    tracker.reset()

    inner.reset.assert_called_once()
    assert predictor.trackers == []
    assert predictor.vid_path == []
    assert tracker._model is model


def test_downscale_leaves_small_frames_alone():
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    assert downscale_for_output(frame).shape == (360, 640, 3)


def test_downscale_caps_1080p_width():
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    out = downscale_for_output(frame, max_width=1280)
    assert out.shape[1] == 1280
    assert out.shape[0] == 720


def test_write_frame_stream_rejects_an_empty_iterator(tmp_path):
    processor = VideoProcessor(tmp_path / "unused.mp4")
    with pytest.raises(VideoReadError, match="No frames"):
        processor.write_frame_stream(tmp_path / "out.mp4", iter(()))


def test_annotate_frame_draws_a_player_box():
    class _Obj:
        class_name = "player"
        track_id = 7
        bbox = [10, 20, 40, 80]

    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    drawn = _annotate_frame(frame, [_Obj()], {7: {"team": "home"}})
    assert drawn.shape == frame.shape
    # The original frame is not mutated.
    assert not np.array_equal(drawn, frame)
