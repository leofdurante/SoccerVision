from app.analytics.zones import all_zone_labels, x_third, y_zone, zone_label


def test_x_third_home_vs_away_perspective():
    assert x_third(10, "home") == "defensive_third"
    assert x_third(50, "home") == "middle_third"
    assert x_third(90, "home") == "final_third"

    # Away attacks the opposite way, so the labeling flips.
    assert x_third(10, "away") == "final_third"
    assert x_third(90, "away") == "defensive_third"


def test_y_zone_bands():
    assert y_zone(5) == "left"
    assert y_zone(50) == "central"
    assert y_zone(95) == "right"


def test_zone_label_and_all_zone_labels():
    assert zone_label(10, 10) == "left_defensive_third"
    assert len(all_zone_labels()) == 9
    assert len(set(all_zone_labels())) == 9
