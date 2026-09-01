import numpy as np

from app.cv.team_classifier import TeamClassifier


def _solid_crop(bgr: tuple[int, int, int], size: int = 40) -> np.ndarray:
    crop = np.zeros((size, size, 3), dtype=np.uint8)
    crop[:, :] = bgr
    return crop


def test_team_classifier_separates_two_distinct_shirt_colors():
    red_crops = [_solid_crop((0, 0, 220)) for _ in range(6)]  # BGR red
    blue_crops = [_solid_crop((220, 0, 0)) for _ in range(6)]  # BGR blue

    classifier = TeamClassifier()
    assert classifier.fit(red_crops + blue_crops) is True

    red_team = classifier.classify(_solid_crop((0, 0, 220)))["team"]
    blue_team = classifier.classify(_solid_crop((220, 0, 0)))["team"]

    assert red_team != blue_team
    assert red_team in ("home", "away")
    assert blue_team in ("home", "away")


def test_team_classifier_consistent_for_same_color_repeated():
    red_crops = [_solid_crop((0, 0, 220)) for _ in range(6)]
    blue_crops = [_solid_crop((220, 0, 0)) for _ in range(6)]
    classifier = TeamClassifier()
    classifier.fit(red_crops + blue_crops)

    results = [classifier.classify(_solid_crop((0, 0, 220)))["team"] for _ in range(5)]
    assert len(set(results)) == 1  # deterministic for identical input


def test_team_classifier_returns_unknown_when_not_fitted():
    classifier = TeamClassifier()
    result = classifier.classify(_solid_crop((0, 0, 220)))
    assert result == {"team": "unknown", "confidence": 0.0}


def test_team_classifier_fit_fails_gracefully_with_too_few_samples():
    classifier = TeamClassifier()
    assert classifier.fit([_solid_crop((0, 0, 220))]) is False
