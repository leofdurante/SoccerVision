"""Pitch zone taxonomy shared by the rest of the analytics package.

Convention (documented MVP simplification): "home" always attacks in the
+x direction (toward x=100), "away" always attacks in the -x direction
(toward x=0), for the whole match. A real broadcast would need to flip
this at half-time; we don't have a half-time signal from CV alone in
this MVP, so it's a known limitation (see README).

Zones are named from home's attacking perspective for readability
("left_final_third" etc.), but numerical-advantage comparisons are made
on the underlying physical zone (same 3x3 grid cell), which is valid
regardless of which team is "attacking" it.
"""

from __future__ import annotations

Team = str

X_THIRDS = ("defensive_third", "middle_third", "final_third")  # from home's perspective
Y_ZONES = ("left", "central", "right")


def x_third(x: float, team: Team) -> str:
    """Which third of the pitch (named from home's attacking perspective)
    an absolute field_x coordinate falls in for the given team."""
    third_index = min(2, int(x // (100 / 3)))
    if team == "away":
        third_index = 2 - third_index  # away attacks the opposite way
    return X_THIRDS[third_index]


def y_zone(y: float) -> str:
    zone_index = min(2, int(y // (100 / 3)))
    return Y_ZONES[zone_index]


def zone_label(x: float, y: float) -> str:
    """Physical zone label, always expressed from home's attacking
    perspective, independent of which team occupies it."""
    third_index = min(2, int(x // (100 / 3)))
    return f"{y_zone(y)}_{X_THIRDS[third_index]}"


def all_zone_labels() -> list[str]:
    return [f"{yz}_{xt}" for xt in X_THIRDS for yz in Y_ZONES]
