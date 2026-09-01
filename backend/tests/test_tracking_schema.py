from app.cv.tracker import TrackedObject


def test_tracked_object_to_dict_shape():
    obj = TrackedObject(
        track_id=17,
        class_name="player",
        bbox=[1.0, 2.0, 3.0, 4.0],
        center=[2.0, 3.0],
        confidence=0.93,
    )
    assert obj.to_dict() == {
        "track_id": 17,
        "class_name": "player",
        "bbox": [1.0, 2.0, 3.0, 4.0],
        "center": [2.0, 3.0],
        "confidence": 0.93,
    }
