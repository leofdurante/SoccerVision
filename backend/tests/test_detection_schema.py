from app.cv.detector import Detection


def test_detection_to_dict_shape():
    detection = Detection(
        class_id=0,
        class_name="player",
        confidence=0.94,
        bbox=[10.0, 20.0, 30.0, 60.0],
        center=[20.0, 40.0],
    )
    data = detection.to_dict()
    assert data == {
        "class_id": 0,
        "class_name": "player",
        "confidence": 0.94,
        "bbox": [10.0, 20.0, 30.0, 60.0],
        "center": [20.0, 40.0],
    }


def test_detection_center_matches_bbox_midpoint():
    x1, y1, x2, y2 = 0.0, 0.0, 10.0, 20.0
    detection = Detection(
        class_id=0,
        class_name="player",
        confidence=0.5,
        bbox=[x1, y1, x2, y2],
        center=[(x1 + x2) / 2, (y1 + y2) / 2],
    )
    assert detection.center == [5.0, 10.0]
