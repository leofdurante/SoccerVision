from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.cv.pitch_view import estimate_visible_pitch, visible_x_span


def _green(h: int = 360, w: int = 640) -> np.ndarray:
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:] = (60, 140, 70)
    return frame


def test_plain_grass_falls_back_to_the_whole_pitch():
    view = estimate_visible_pitch(_green())
    assert view is not None
    assert view.pitch_corners[0][0] == pytest.approx(0, abs=1)
    assert view.pitch_corners[1][0] == pytest.approx(100, abs=1)


def test_centre_circle_in_the_middle_maps_to_a_middle_slice():
    x0, x1, label, conf = visible_x_span(
        circle=(50.0, 50.0, 15.0),
        turf=(0, 0, 100, 100),
        densities=(8.0, 12.0, 8.0),
        halfway_line=True,
    )
    assert label == "middle_third"
    assert conf >= 0.7
    assert x0 > 10
    assert x1 < 90
    assert x0 < 50 < x1


def test_centre_circle_on_the_left_means_we_are_looking_right():
    """If the centre spot is on the left of the frame, most of what is
    visible is the right half of the pitch — the camera has panned past
    halfway toward the far goal."""
    x0, x1, label, _ = visible_x_span(
        circle=(20.0, 50.0, 15.0),
        turf=(0, 0, 100, 100),
        densities=(8.0, 8.0, 8.0),
        halfway_line=True,
    )
    assert x1 > 80
    assert (x0 + x1) / 2 > 50
    assert label == "right_third"


def test_centre_circle_on_the_right_means_we_are_looking_left():
    x0, x1, label, _ = visible_x_span(
        circle=(80.0, 50.0, 15.0),
        turf=(0, 0, 100, 100),
        densities=(8.0, 8.0, 8.0),
        halfway_line=True,
    )
    assert x0 < 20
    assert (x0 + x1) / 2 < 50
    assert label == "left_third"


def test_penalty_paint_piled_on_the_left_is_the_left_third():
    x0, x1, label, _ = visible_x_span(
        circle=None,
        turf=(0, 0, 100, 100),
        densities=(40.0, 8.0, 4.0),
        halfway_line=False,
    )
    assert label == "left_third"
    assert x1 <= 40
    assert x0 == pytest.approx(0, abs=0.5)


def test_penalty_paint_piled_on_the_right_is_the_right_third():
    x0, x1, label, _ = visible_x_span(
        circle=None,
        turf=(0, 0, 100, 100),
        densities=(4.0, 8.0, 40.0),
        halfway_line=False,
    )
    assert label == "right_third"
    assert x0 >= 60


def test_halfway_line_without_a_circle_still_reads_as_midfield():
    x0, x1, label, _ = visible_x_span(
        circle=None,
        turf=(0, 0, 100, 100),
        densities=(10.0, 20.0, 10.0),
        halfway_line=True,
    )
    assert label == "middle_third"
    assert x0 == pytest.approx(30, abs=1)
    assert x1 == pytest.approx(70, abs=1)


def test_drawn_centre_circle_is_detected_as_a_middle_slice():
    frame = _green()
    # Large circle = camera is tight on midfield, so the visible slice
    # should be well inside 0–100 rather than stretched across the pitch.
    cv2.circle(frame, (320, 200), 110, (230, 230, 230), 4)
    cv2.line(frame, (320, 40), (320, 350), (230, 230, 230), 3)
    view = estimate_visible_pitch(frame)
    assert view is not None
    x0, x1 = view.pitch_corners[0][0], view.pitch_corners[1][0]
    assert view.label == "middle_third"
    assert x1 - x0 < 70
    assert x0 < 50 < x1
