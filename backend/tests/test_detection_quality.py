"""Detection accuracy and track-identity stability.

Two problems these guard against, both measured on real match footage:

1. A stadium shot contains substitutes, coaches, officials and spectators,
   and the person detector returns all of them. Only people standing on the
   playing surface count.
2. The broadcast scorebug sits still near the top of frame all match, so it
   is detected every frame and the tracker rewards it with the longest,
   most consistent "player" track in the analysis — 197 samples, versus a
   median of 12 for real players.
"""

from __future__ import annotations

import numpy as np

from app.cv.tracker import _feet_on_surface, _playing_surface_mask
from app.services.analysis_service import (
    _drop_short_tracks,
    _drop_static_overlay_tracks,
    _on_pitch,
    _player_feet,
    _strip_discarded_tracks,
)

FRAME_H, FRAME_W = 360, 640


def _frame_with_turf(turf_top: int = 120) -> np.ndarray:
    """BGR frame: dark stands on top, green turf below."""
    frame = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
    frame[:turf_top] = (40, 40, 45)      # stands / track
    frame[turf_top:] = (60, 140, 70)     # turf
    return frame


# --- playing-surface filter ---------------------------------------------


def test_turf_is_detected_as_the_playing_surface():
    mask = _playing_surface_mask(_frame_with_turf())
    assert mask[300, 320] > 0, "turf should be inside the mask"
    assert mask[20, 320] == 0, "stands should not be"


def test_a_player_standing_on_turf_is_kept():
    mask = _playing_surface_mask(_frame_with_turf())
    # feet at y=300, well onto the turf
    assert _feet_on_surface(mask, (310, 260, 330, 300))


def test_someone_standing_off_the_turf_is_rejected():
    mask = _playing_surface_mask(_frame_with_turf())
    # feet at y=60, up in the stands
    assert not _feet_on_surface(mask, (310, 20, 330, 60))


def test_an_unreadable_box_is_kept_rather_than_dropped():
    """Ambiguity should never silently delete a real player."""
    mask = _playing_surface_mask(_frame_with_turf())
    assert _feet_on_surface(mask, (700, 400, 720, 500)), "off-frame box should be kept"


# --- static overlay tracks ----------------------------------------------


def _track(n: int, x: float, y: float, drift: float) -> list[dict]:
    """n samples walking `drift` px per step from (x, y)."""
    return [
        {"center": [x + i * drift, y + i * drift], "bbox": [x, y, x + 12, y + 30]}
        for i in range(n)
    ]


def test_a_long_stationary_track_high_in_frame_is_dropped():
    """The scorebug: many samples, top of frame, no movement."""
    tracks = {41: _track(197, 237, 20, 0.0)}
    removed = _drop_static_overlay_tracks(tracks, FRAME_H)
    assert removed == [41]
    assert tracks == {}


def test_a_moving_track_high_in_frame_is_kept():
    """A distant player near the top still moves."""
    tracks = {7: _track(197, 237, 20, 2.0)}
    assert _drop_static_overlay_tracks(tracks, FRAME_H) == []
    assert 7 in tracks


def test_a_stationary_player_low_in_frame_is_kept():
    """A goalkeeper can stand still — position in frame is what differs."""
    tracks = {9: _track(197, 300, 300, 0.0)}
    assert _drop_static_overlay_tracks(tracks, FRAME_H) == []
    assert 9 in tracks


def test_a_short_stationary_track_is_kept():
    """Briefly still is not the same as being a graphic."""
    tracks = {5: _track(10, 237, 20, 0.0)}
    assert _drop_static_overlay_tracks(tracks, FRAME_H) == []
    assert 5 in tracks


def test_real_players_survive_alongside_an_overlay():
    tracks = {
        41: _track(197, 237, 20, 0.0),    # scorebug
        1: _track(120, 300, 250, 1.5),
        2: _track(80, 150, 200, 2.0),
        3: _track(60, 400, 280, 0.8),
    }
    removed = _drop_static_overlay_tracks(tracks, FRAME_H)
    assert removed == [41]
    assert set(tracks) == {1, 2, 3}


def test_zero_height_frame_is_handled():
    tracks = {1: _track(100, 10, 10, 0.0)}
    assert _drop_static_overlay_tracks(tracks, 0) == []


# --- in-pitch filter and short tracks -----------------------------------


def test_on_pitch_keeps_the_centre_and_rejects_the_stands():
    assert _on_pitch(50.0, 50.0)
    assert _on_pitch(0.0, 0.0)
    assert _on_pitch(100.0, 100.0)
    assert not _on_pitch(-10.0, 50.0)
    assert not _on_pitch(50.0, 130.0)


def test_player_feet_are_the_bottom_centre_of_the_box():
    assert _player_feet([10.0, 20.0, 30.0, 80.0]) == (20.0, 80.0)


def test_flicker_tracks_are_dropped_and_real_ones_kept():
    tracks = {
        1: _track(20, 300, 250, 1.5),
        2: _track(2, 150, 200, 2.0),
        3: _track(8, 400, 280, 0.8),
    }
    removed = _drop_short_tracks(tracks, min_samples=8)
    assert removed == [2]
    assert set(tracks) == {1, 3}


def test_discarded_ids_are_stripped_from_every_frame():
    class _Obj:
        def __init__(self, track_id: int):
            self.track_id = track_id

    per_frame = [(0.0, [_Obj(1), _Obj(2)]), (0.2, [_Obj(2)])]
    crops = {1: ["a"], 2: ["b"]}
    stripped = _strip_discarded_tracks(per_frame, {2}, crops)
    assert [o.track_id for o in stripped[0][1]] == [1]
    assert stripped[1][1] == []
    assert 2 not in crops
