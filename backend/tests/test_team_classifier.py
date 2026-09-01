import numpy as np

from app.cv.team_classifier import TeamClassifier, hsv_distance, parse_hex_to_hsv


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


def test_parse_hex_accepts_hash_and_bare():
    with_hash = parse_hex_to_hsv("#ff0000")
    bare = parse_hex_to_hsv("ff0000")
    assert with_hash == bare
    assert with_hash[0] < 15  # red sits near hue 0


def test_named_kits_label_home_and_away_correctly():
    red = parse_hex_to_hsv("#dc2626")
    blue = parse_hex_to_hsv("#1d4ed8")
    classifier = TeamClassifier(manual_team_colors={"home": blue, "away": red})
    assert classifier.fit([]) is True
    assert classifier.classify(_solid_crop((220, 0, 0)))["team"] == "home"  # BGR blue
    assert classifier.classify(_solid_crop((0, 0, 220)))["team"] == "away"  # BGR red


def test_named_kits_reject_a_third_colour():
    red = parse_hex_to_hsv("#dc2626")
    blue = parse_hex_to_hsv("#1d4ed8")
    classifier = TeamClassifier(manual_team_colors={"home": blue, "away": red})
    classifier.fit([])
    # Dark jacket — typical ref/coach, not either chromatic kit.
    result = classifier.classify(_solid_crop((40, 40, 40)))
    assert result["team"] == "unknown"
    # Fluorescent steward bib.
    bib = classifier.classify(_solid_crop((0, 255, 80)))
    assert bib["team"] == "unknown"


def test_white_and_black_kits_are_not_confused():
    white = parse_hex_to_hsv("#f5f5f5")
    black = parse_hex_to_hsv("#1a1a1a")
    classifier = TeamClassifier(manual_team_colors={"home": white, "away": black})
    classifier.fit([])
    assert classifier.classify(_solid_crop((245, 245, 245)))["team"] == "home"
    assert classifier.classify(_solid_crop((20, 20, 20)))["team"] == "away"


def test_hsv_distance_is_small_for_the_same_hue():
    red = parse_hex_to_hsv("#e11d48")
    also_red = parse_hex_to_hsv("#be123c")
    blue = parse_hex_to_hsv("#2563eb")
    assert hsv_distance(red, also_red) < hsv_distance(red, blue)
