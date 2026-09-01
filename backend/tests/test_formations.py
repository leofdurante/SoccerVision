from app.analytics.formations import estimate_formation


def test_estimate_formation_detects_four_four_two_shape():
    # Home attacks +x. GK is the single deepest player and gets excluded.
    positions = [
        (3, 50),  # goalkeeper
        # back four
        (20, 10), (20, 35), (20, 65), (20, 90),
        # midfield four
        (50, 15), (50, 40), (50, 60), (50, 85),
        # front two
        (80, 35), (80, 65),
    ]
    result = estimate_formation(positions, team="home")
    assert result["formation"] == "4-4-2"
    assert 0.0 < result["confidence"] <= 1.0


def test_estimate_formation_returns_none_with_too_few_players():
    result = estimate_formation([(10, 10), (20, 20), (30, 30)], team="home")
    assert result == {"formation": None, "confidence": 0.0}


def test_estimate_formation_accounts_for_away_attacking_direction():
    # Away attacks -x, so their goalkeeper sits at high x, defenders next, etc.
    positions = [
        (97, 50),  # goalkeeper
        (80, 10), (80, 35), (80, 65), (80, 90),
        (50, 15), (50, 40), (50, 60), (50, 85),
        (20, 35), (20, 65),
    ]
    result = estimate_formation(positions, team="away")
    assert result["formation"] == "4-4-2"
