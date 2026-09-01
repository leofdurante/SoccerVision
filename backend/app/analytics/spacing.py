"""Team shape metrics computed from normalized field positions.

All functions take a list of (field_x, field_y) tuples for one team at
one instant and return a plain float/tuple, so they're trivial to unit
test with hand-specified coordinates (see backend/tests).
"""

from __future__ import annotations

import math

Point = tuple[float, float]


def team_width(positions: list[Point]) -> float | None:
    """Horizontal (y-axis) spread: distance between the widest players."""
    if len(positions) < 2:
        return None
    ys = [p[1] for p in positions]
    return max(ys) - min(ys)


def team_depth(positions: list[Point]) -> float | None:
    """Vertical (x-axis, i.e. length-of-pitch) spread: deepest to highest player."""
    if len(positions) < 2:
        return None
    xs = [p[0] for p in positions]
    return max(xs) - min(xs)


def team_centroid(positions: list[Point]) -> Point | None:
    if not positions:
        return None
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _pairwise_distances(positions: list[Point]) -> list[float]:
    distances = []
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            dx = positions[i][0] - positions[j][0]
            dy = positions[i][1] - positions[j][1]
            distances.append(math.hypot(dx, dy))
    return distances


def average_spacing(positions: list[Point]) -> float | None:
    """Average pairwise distance between all players on the team."""
    distances = _pairwise_distances(positions)
    if not distances:
        return None
    return sum(distances) / len(distances)


def compactness(positions: list[Point]) -> float | None:
    """0..1 score, higher = more tightly grouped.

    Defined as the inverse of the average distance from each player to
    the team centroid, normalized against half the pitch diagonal
    (~70.7 units) so the score stays in a legible 0..1 range for
    realistic team shapes.
    """
    centroid = team_centroid(positions)
    if centroid is None or len(positions) < 2:
        return None
    avg_dist_to_centroid = sum(
        math.hypot(p[0] - centroid[0], p[1] - centroid[1]) for p in positions
    ) / len(positions)
    pitch_half_diagonal = math.hypot(100, 100) / 2
    score = 1.0 - min(1.0, avg_dist_to_centroid / pitch_half_diagonal)
    return round(score, 3)


def defensive_line_height(positions: list[Point], team: str, num_defenders: int = 4) -> float | None:
    """How far up the pitch the defensive line is pushed, as a 0..100
    value measured from the team's own goal line (0 = on their own goal
    line, 100 = fully advanced to the opponent's goal line).

    Approximated as the mean field_x of the deepest `num_defenders`
    outfield players (deepest = closest to their own goal), excluding
    the presumed goalkeeper (the single most extreme player).
    """
    if len(positions) < 2:
        return None

    xs = sorted((p[0] for p in positions), reverse=(team == "away"))
    # xs[0] is the deepest player (closest to own goal) = presumed GK; drop it.
    outfield = xs[1:]
    if not outfield:
        return None
    defenders = outfield[: min(num_defenders, len(outfield))]
    mean_x = sum(defenders) / len(defenders)
    return round(mean_x if team == "home" else 100 - mean_x, 2)


def count_in_thirds(positions_with_team: list[tuple[Point, str]]) -> dict[str, int]:
    """Convenience for metrics endpoint: counts per (team-relative) third."""
    from app.analytics.zones import x_third

    counts = {"defensive_third": 0, "middle_third": 0, "final_third": 0}
    for (x, _y), team in positions_with_team:
        counts[x_third(x, team)] += 1
    return counts
