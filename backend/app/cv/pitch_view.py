"""Estimate which *part* of the pitch is in the camera this frame.

A panning broadcast almost never shows the whole field. Stretching the
visible rectangle onto 0–100 makes every on-screen player look like they
span the full pitch. Humans don't do that: they see the centre circle,
halfway line or a penalty box and know which slice they are looking at.

This module finds those painted landmarks and returns a homography that
maps the visible turf onto the matching sub-rectangle of the 0–100 pitch
(x along the length, y along the width) instead of the whole field.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.cv.field_mapper import FIELD_HEIGHT, FIELD_WIDTH, estimate_pitch_image_corners

# Centre circle radius is 9.15 m on a ~105 m pitch ≈ 8.7 units of 0–100 x.
_CIRCLE_RADIUS_PITCH = 8.7

# White paint: high value, low saturation, and it has to sit on/near turf
# so stadium lights and shirts don't count as lines.
_WHITE_LOW = (0, 0, 170)
_WHITE_HIGH = (180, 70, 255)


@dataclass(frozen=True)
class VisiblePitch:
    """Image quad and the pitch-space quad it corresponds to.

    Both quads are top-left, top-right, bottom-right, bottom-left.
    """

    image_corners: list[list[float]]
    pitch_corners: list[list[float]]
    label: str
    confidence: float


def _white_line_mask(frame: np.ndarray, grass: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    white = cv2.inRange(hsv, _WHITE_LOW, _WHITE_HIGH)
    near_grass = cv2.dilate(grass, np.ones((11, 11), np.uint8))
    lines = cv2.bitwise_and(white, near_grass)
    return cv2.morphologyEx(lines, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))


def _turf_bbox(image_corners: list[list[float]]) -> tuple[int, int, int, int]:
    xs = [p[0] for p in image_corners]
    ys = [p[1] for p in image_corners]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def _detect_center_circle(
    line_mask: np.ndarray, turf: tuple[int, int, int, int]
) -> tuple[float, float, float] | None:
    """Return (cx, cy, radius) in pixels, or None."""
    x0, y0, x1, y1 = turf
    width, height = max(1, x1 - x0), max(1, y1 - y0)
    min_r = max(8, int(0.04 * min(width, height)))
    max_r = max(min_r + 4, int(0.28 * min(width, height)))

    blurred = cv2.GaussianBlur(line_mask, (9, 9), 0)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(width, height) / 2,
        param1=80,
        param2=18,
        minRadius=min_r,
        maxRadius=max_r,
    )
    if circles is None:
        return None

    best = None
    best_score = -1.0
    for cx, cy, radius in circles[0]:
        if not (x0 <= cx <= x1 and y0 <= cy <= y1):
            continue
        # Prefer a circle whose centre sits on turf-ish lines (the centre spot).
        patch = line_mask[
            max(0, int(cy) - 3) : int(cy) + 4,
            max(0, int(cx) - 3) : int(cx) + 4,
        ]
        score = float(radius) + (0.5 if patch.size and patch.mean() > 10 else 0.0)
        if score > best_score:
            best_score = score
            best = (float(cx), float(cy), float(radius))
    return best


def _line_density_thirds(line_mask: np.ndarray, turf: tuple[int, int, int, int]) -> tuple[float, float, float]:
    x0, y0, x1, y1 = turf
    width = max(1, x1 - x0)
    t = width // 3
    left = line_mask[y0:y1, x0 : x0 + t]
    mid = line_mask[y0:y1, x0 + t : x0 + 2 * t]
    right = line_mask[y0:y1, x0 + 2 * t : x1]
    return (
        float(left.mean()) if left.size else 0.0,
        float(mid.mean()) if mid.size else 0.0,
        float(right.mean()) if right.size else 0.0,
    )


def _has_central_dividing_line(line_mask: np.ndarray, turf: tuple[int, int, int, int]) -> bool:
    """A long near-vertical stroke through the middle of the turf ≈ halfway line."""
    x0, y0, x1, y1 = turf
    width, height = max(1, x1 - x0), max(1, y1 - y0)
    lines = cv2.HoughLinesP(
        line_mask,
        1,
        np.pi / 180,
        threshold=max(20, height // 8),
        minLineLength=max(20, int(0.35 * height)),
        maxLineGap=20,
    )
    if lines is None:
        return False
    mid_x = (x0 + x1) / 2
    for x_a, y_a, x_b, y_b in lines[:, 0]:
        dx, dy = abs(int(x_b) - int(x_a)), abs(int(y_b) - int(y_a))
        if dy < dx * 1.2:
            continue  # not upright enough to be a halfway line in a sideline pan
        mx = (int(x_a) + int(x_b)) / 2
        if abs(mx - mid_x) < 0.18 * width:
            return True
    return False


def visible_x_span(
    *,
    circle: tuple[float, float, float] | None,
    turf: tuple[int, int, int, int],
    densities: tuple[float, float, float],
    halfway_line: bool,
) -> tuple[float, float, str, float]:
    """Pitch-space x interval [x0, x1] that the camera is looking at."""
    x0_px, _, x1_px, _ = turf
    turf_w = max(1.0, x1_px - x0_px)
    left_d, mid_d, right_d = densities

    if circle is not None:
        cx, _, radius = circle
        fx = float(np.clip((cx - x0_px) / turf_w, 0.0, 1.0))
        radius_frac = float(np.clip(radius / turf_w, 0.04, 0.4))
        span = float(np.clip(_CIRCLE_RADIUS_PITCH / radius_frac, 28.0, 90.0))
        x0 = 50.0 - fx * span
        x1 = 50.0 + (1.0 - fx) * span
        x0, x1 = max(0.0, x0), min(FIELD_WIDTH, x1)
        if x1 - x0 < 20:
            pad = (20 - (x1 - x0)) / 2
            x0, x1 = max(0.0, x0 - pad), min(FIELD_WIDTH, x1 + pad)
        return x0, x1, "middle_third" if 35 <= (x0 + x1) / 2 <= 65 else (
            "left_third" if (x0 + x1) / 2 < 50 else "right_third"
        ), 0.8

    if halfway_line and mid_d >= left_d and mid_d >= right_d:
        return 30.0, 70.0, "middle_third", 0.55

    # Penalty-box / end-zone paint piles up on one side of a tight pan.
    if left_d > right_d * 1.35 and left_d > mid_d * 0.9:
        return 0.0, 38.0, "left_third", 0.5
    if right_d > left_d * 1.35 and right_d > mid_d * 0.9:
        return 62.0, 100.0, "right_third", 0.5

    if max(left_d, mid_d, right_d) < 4:
        return 0.0, FIELD_WIDTH, "unknown", 0.15

    return 0.0, FIELD_WIDTH, "full", 0.35


def estimate_visible_pitch(frame: np.ndarray) -> VisiblePitch | None:
    """Landmark-based view of the pitch, or None if there is no turf."""
    from app.cv.tracker import _playing_surface_mask

    grass = _playing_surface_mask(frame)
    image_corners = estimate_pitch_image_corners(frame)
    if image_corners is None:
        return None

    turf = _turf_bbox(image_corners)
    lines = _white_line_mask(frame, grass)
    circle = _detect_center_circle(lines, turf)
    densities = _line_density_thirds(lines, turf)
    halfway = _has_central_dividing_line(lines, turf) if circle is None else True

    x0, x1, label, confidence = visible_x_span(
        circle=circle, turf=turf, densities=densities, halfway_line=halfway
    )
    pitch_corners = [
        [x0, 0.0],
        [x1, 0.0],
        [x1, FIELD_HEIGHT],
        [x0, FIELD_HEIGHT],
    ]
    return VisiblePitch(
        image_corners=image_corners,
        pitch_corners=pitch_corners,
        label=label,
        confidence=confidence,
    )
