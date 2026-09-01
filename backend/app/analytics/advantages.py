"""Numerical advantage detection — headline feature.

Divides the pitch into the 3x3 zone grid from `app.analytics.zones` and
compares home vs. away player counts per zone. A zone is flagged when
one team outnumbers the other by at least `MIN_ADVANTAGE_MARGIN` and at
least one team has >= `MIN_PLAYERS_FOR_SIGNAL` players present, to avoid
flagging noise from a single stray player.
"""

from __future__ import annotations

from app.analytics.zones import all_zone_labels, zone_label

MIN_ADVANTAGE_MARGIN = 1
MIN_PLAYERS_FOR_SIGNAL = 2

Point = tuple[float, float]


def find_numerical_advantages(
    home_positions: list[Point], away_positions: list[Point]
) -> list[dict]:
    """Returns a list of {"zone", "home_count", "away_count",
    "advantage_team", "advantage_label"} for every zone with a
    qualifying imbalance."""
    zone_counts: dict[str, dict[str, int]] = {z: {"home": 0, "away": 0} for z in all_zone_labels()}

    for x, y in home_positions:
        zone_counts[zone_label(x, y)]["home"] += 1
    for x, y in away_positions:
        zone_counts[zone_label(x, y)]["away"] += 1

    advantages = []
    for zone, counts in zone_counts.items():
        home_count, away_count = counts["home"], counts["away"]
        larger, smaller = max(home_count, away_count), min(home_count, away_count)
        if larger < MIN_PLAYERS_FOR_SIGNAL:
            continue
        if larger - smaller < MIN_ADVANTAGE_MARGIN:
            continue
        advantage_team = "home" if home_count > away_count else "away"
        advantages.append(
            {
                "zone": zone,
                "home_count": home_count,
                "away_count": away_count,
                "advantage_team": advantage_team,
                "advantage_label": f"{larger}v{smaller}",
            }
        )
    return advantages
