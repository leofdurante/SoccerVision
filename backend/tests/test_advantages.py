"""Numerical advantage detection tests.

Per spec section 24, uses manually-specified coordinates for a team with
4 players against a team with 3 players who should be recognized as
sharing one tactical zone. The exact figures in the spec's illustrative
example straddle a zone boundary under a strict 3x3 grid (e.g. x=60 and
x=72 fall in different pitch thirds), so the coordinates below keep the
same 4-vs-3 shape but are chosen to land inside a single zone
unambiguously, per the spec's own success criterion: "the analytics
engine should detect an appropriate local numerical advantage when those
players fall within the same tactical zone."
"""

from app.analytics.advantages import find_numerical_advantages


def test_four_v_three_overload_detected_in_shared_zone():
    home_positions = [(70, 70), (75, 75), (80, 72), (78, 85)]  # right final third
    away_positions = [(72, 80), (76, 78), (79, 90)]

    advantages = find_numerical_advantages(home_positions, away_positions)

    assert len(advantages) == 1
    advantage = advantages[0]
    assert advantage["zone"] == "right_final_third"
    assert advantage["home_count"] == 4
    assert advantage["away_count"] == 3
    assert advantage["advantage_team"] == "home"
    assert advantage["advantage_label"] == "4v3"


def test_no_advantage_when_teams_are_balanced():
    home_positions = [(10, 10), (10, 20)]
    away_positions = [(12, 12), (12, 22)]
    assert find_numerical_advantages(home_positions, away_positions) == []


def test_no_advantage_below_minimum_player_signal():
    # A single home player with zero away players nearby shouldn't count
    # as a meaningful "overload" — too little signal.
    home_positions = [(10, 10)]
    away_positions = []
    assert find_numerical_advantages(home_positions, away_positions) == []


def test_multiple_zones_can_each_report_advantages():
    home_positions = [(10, 10), (10, 15), (90, 90), (90, 95)]
    away_positions = [(10, 12)]
    advantages = find_numerical_advantages(home_positions, away_positions)
    zones = {a["zone"] for a in advantages}
    assert "left_defensive_third" in zones
    assert all(a["advantage_team"] == "home" for a in advantages)
