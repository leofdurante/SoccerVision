"""Camera-view → normalized pitch coordinate mapping via homography.

MVP approach (per spec): manually configured field points. A real product
would auto-detect pitch lines; here we assume a fixed camera position for
a given video and let 4 image-space corner points be configured (default:
the full source frame, i.e. the camera is assumed to already show the
whole pitch, corner to corner — a common simplification for a single
tactical/broadcast camera in a hackathon demo).

Normalized pitch coordinates follow the spec's convention:
  x: 0 (left goal line)   -> 100 (right goal line)
  y: 0 (top touchline)    -> 100 (bottom touchline)
"""

from __future__ import annotations

import numpy as np

FIELD_WIDTH = 100.0
FIELD_HEIGHT = 100.0

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


class FieldMapper:
    def __init__(self):
        self._h_image_to_field: np.ndarray | None = None
        self._h_field_to_image: np.ndarray | None = None

    def calculate_homography(
        self,
        frame_width: int,
        frame_height: int,
        image_corners: list[list[float]] | None = None,
    ) -> None:
        """`image_corners` is the same 4-point order as `_PITCH_CORNERS`
        (top-left, top-right, bottom-right, bottom-left) in pixel space.
        Defaults to the full frame if not provided — the MVP assumption
        that the camera already frames the whole pitch."""
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

        self._h_image_to_field = cv2.getPerspectiveTransform(src, _PITCH_CORNERS)
        self._h_field_to_image = cv2.getPerspectiveTransform(_PITCH_CORNERS, src)

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
