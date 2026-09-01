import numpy as np
import pytest

from app.cv.field_mapper import FieldMapper, FieldMappingError


def test_calculate_homography_maps_frame_corners_to_pitch_corners():
    mapper = FieldMapper()
    mapper.calculate_homography(frame_width=1000, frame_height=500)

    top_left = mapper.image_to_field((0, 0))
    bottom_right = mapper.image_to_field((1000, 500))
    center = mapper.image_to_field((500, 250))

    assert top_left == pytest.approx((0, 0), abs=0.5)
    assert bottom_right == pytest.approx((100, 100), abs=0.5)
    assert center == pytest.approx((50, 50), abs=0.5)


def test_field_to_image_is_inverse_of_image_to_field():
    mapper = FieldMapper()
    mapper.calculate_homography(frame_width=1280, frame_height=720)

    original = (317.0, 481.0)
    field_point = mapper.image_to_field(original)
    round_tripped = mapper.field_to_image(field_point)

    assert round_tripped == pytest.approx(original, abs=0.5)


def test_methods_raise_before_homography_calculated():
    mapper = FieldMapper()
    with pytest.raises(FieldMappingError):
        mapper.image_to_field((0, 0))
    with pytest.raises(FieldMappingError):
        mapper.field_to_image((0, 0))


def test_custom_image_corners():
    mapper = FieldMapper()
    # A trapezoidal camera view (perspective effect) instead of a flat rectangle.
    mapper.calculate_homography(
        frame_width=1000,
        frame_height=500,
        image_corners=[[100, 0], [900, 0], [1000, 500], [0, 500]],
    )
    top_left_field = mapper.image_to_field((100, 0))
    assert top_left_field == pytest.approx((0, 0), abs=0.5)


def test_pitch_corners_follow_the_turf_not_the_stands():
    from app.cv.field_mapper import estimate_pitch_image_corners

    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:120] = (40, 40, 45)
    frame[120:] = (60, 140, 70)
    corners = estimate_pitch_image_corners(frame)
    assert corners is not None
    # Top edge of the pitch should sit on the turf, not the stands.
    assert corners[0][1] == pytest.approx(120, abs=5)
    assert corners[2][1] == pytest.approx(359, abs=2)


def test_pitch_corners_are_none_when_there_is_no_turf():
    from app.cv.field_mapper import estimate_pitch_image_corners

    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:] = (40, 40, 45)
    assert estimate_pitch_image_corners(frame) is None
