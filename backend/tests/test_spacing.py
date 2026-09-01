import pytest

from app.analytics.spacing import (
    average_spacing,
    compactness,
    team_centroid,
    team_depth,
    team_width,
)


def test_team_width_and_depth():
    positions = [(10, 10), (10, 90), (50, 50)]
    assert team_width(positions) == 80  # y: 90 - 10
    assert team_depth(positions) == 40  # x: 50 - 10


def test_team_centroid():
    positions = [(0, 0), (10, 0), (5, 10)]
    cx, cy = team_centroid(positions)
    assert cx == pytest.approx(5.0)
    assert cy == pytest.approx(10 / 3)


def test_average_spacing_two_players():
    positions = [(0, 0), (3, 4)]
    assert average_spacing(positions) == pytest.approx(5.0)  # 3-4-5 triangle


def test_compactness_tighter_group_scores_higher():
    tight = [(50, 50), (52, 51), (49, 48)]
    loose = [(0, 0), (100, 100), (0, 100)]
    assert compactness(tight) > compactness(loose)


def test_metrics_return_none_for_insufficient_players():
    assert team_width([(1, 1)]) is None
    assert team_depth([]) is None
    assert average_spacing([(1, 1)]) is None
