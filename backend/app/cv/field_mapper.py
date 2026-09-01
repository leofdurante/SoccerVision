"""Camera-view → normalized pitch coordinate mapping via homography.

MVP approach: map the *visible* slice of the pitch, not the whole field.

A panning camera almost never shows corner-to-corner. The 4 image points
are the visible turf quad; the 4 destination points are the matching
sub-rectangle of the 0–100 pitch (centre circle / halfway line / box),
estimated per frame in `pitch_view.py`. Full-frame = full-pitch remains
the fallback when no landmarks are found.

Normalized pitch coordinates follow the spec's convention:
  x: 0 (left goal line)   -> 100 (right goal line)
  y: 0 (top touchline)    -> 100 (bottom touchline)
"""

from __future__ import annotations

import numpy as np

FIELD_WIDTH = 100.0
FIELD_HEIGHT = 100.0

# Fraction of the frame that must look like turf before we trust the mask
# as the pitch (otherwise fall back to the full frame).
_MIN_TURF_COVERAGE = 0.15

# Destination points: the four pitch corners in normalized space, in the
# same order as the image-space source points must be supplied
# (top-left, top-right, bottom-right, bottom-left).
_PITCH_CORNERS = np.array(
    [
        [0.0, 0.0],
        [FIELD_WIDTH, 0.0],
        [FIELD_WIDTH, FIELD_HEIGHT],
        [0.0, FIELD_HEIGHT],
    ],
    dtype=np.float32,
)


class FieldMappingError(RuntimeError):
    pass


def estimate_pitch_image_corners(frame: np.ndarray) -> list[list[float]] | None:
    """Bounding rectangle of the playing surface in pixel space.

    Returns the 4-point order expected by `FieldMapper.calculate_homography`,
    or None when the turf mask is too small to trust (dark indoor shot,
    failed colour filter). Callers should keep the full-frame default.
    """
    from app.cv.tracker import _playing_surface_mask

    mask = _playing_surface_mask(frame)
    ys, xs = np.where(mask > 0)
    if mask.size == 0 or (len(xs) / mask.size) < _MIN_TURF_COVERAGE:
        return None

    x_min, x_max = float(xs.min()), float(xs.max())
    y_min, y_max = float(ys.min()), float(ys.max())
    return [
        [x_min, y_min],
        [x_max, y_min],
        [x_max, y_max],
        [x_min, y_max],
    ]


class FieldMapper:
    def __init__(self, smooth: float = 0.7):
        self._h_image_to_field: np.ndarray | None = None
        self._h_field_to_image: np.ndarray | None = None
        self._smooth = float(np.clip(smooth, 0.0, 0.95))
        self._image_corners: np.ndarray | None = None
        self._pitch_corners: np.ndarray | None = None
        self.last_label: str = "full"
        self._view_seeded = False

    @property
    def is_ready(self) -> bool:
        return self._h_image_to_field is not None

    def calculate_homography(
        self,
        frame_width: int,
        frame_height: int,
        image_corners: list[list[float]] | None = None,
        pitch_corners: list[list[float]] | None = None,
    ) -> None:
        """`image_corners` is the same 4-point order as `_PITCH_CORNERS`
        (top-left, top-right, bottom-right, bottom-left) in pixel space.
        `pitch_corners` is that same order in 0–100 pitch space; omitted
        it means the whole pitch, which is the old full-frame assumption."""
        import cv2

        if image_corners is None:
            image_corners = [
                [0.0, 0.0],
                [frame_width, 0.0],
                [frame_width, frame_height],
                [0.0, frame_height],
            ]

        src = np.array(image_corners, dtype=np.float32)
        if src.shape != (4, 2):
            raise FieldMappingError("image_corners must contain exactly 4 [x, y] points")

        dst = np.array(pitch_corners, dtype=np.float32) if pitch_corners is not None else _PITCH_CORNERS
        if dst.shape != (4, 2):
            raise FieldMappingError("pitch_corners must contain exactly 4 [x, y] points")

        self._image_corners = src
        self._pitch_corners = dst
        self._h_image_to_field = cv2.getPerspectiveTransform(src, dst)
        self._h_field_to_image = cv2.getPerspectiveTransform(dst, src)

    def update_visible_view(
        self,
        frame_width: int,
        frame_height: int,
        image_corners: list[list[float]],
        pitch_corners: list[list[float]],
        label: str = "full",
    ) -> None:
        """Recompute homography for this frame, easing toward the new view.

        A pan would otherwise slam players from midfield to a goal in one
        sample whenever the landmark detector flips labels.
        """
        src = np.array(image_corners, dtype=np.float32)
        dst = np.array(pitch_corners, dtype=np.float32)
        if self._view_seeded and self._image_corners is not None and self._pitch_corners is not None:
            src = self._smooth * self._image_corners + (1.0 - self._smooth) * src
            dst = self._smooth * self._pitch_corners + (1.0 - self._smooth) * dst
        self._view_seeded = True
        self.last_label = label
        self.calculate_homography(
            frame_width,
            frame_height,
            image_corners=src.tolist(),
            pitch_corners=dst.tolist(),
        )

    def image_to_field(self, point: tuple[float, float]) -> tuple[float, float]:
        if self._h_image_to_field is None:
            raise FieldMappingError("calculate_homography() must be called before image_to_field()")
        return self._transform(point, self._h_image_to_field)

    def field_to_image(self, point: tuple[float, float]) -> tuple[float, float]:
        if self._h_field_to_image is None:
            raise FieldMappingError("calculate_homography() must be called before field_to_image()")
        return self._transform(point, self._h_field_to_image)

    @staticmethod
    def _transform(point: tuple[float, float], matrix: np.ndarray) -> tuple[float, float]:
        vec = np.array([point[0], point[1], 1.0])
        result = matrix @ vec
        result /= result[2]
        return float(result[0]), float(result[1])
