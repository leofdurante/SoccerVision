"""Simple proximity-based possession heuristic.

Explicitly NOT a real possession model. At each sampled frame where the
ball was detected, whichever tracked player is closest to the ball
(within `MAX_POSSESSION_DISTANCE` field units) is credited with
possession for that frame. Aggregated across the whole video this gives
a rough estimated possession split, always labeled "estimated" at the
API layer (see schemas.MetricsResponse.possession_estimate).
"""

from __future__ import annotations

import math

MAX_POSSESSION_DISTANCE = 6.0  # field units (pitch is 100x100); ~ a few meters


def nearest_player_to_ball(
    ball_field_pos: tuple[float, float],
    players: list[dict],  # each: {"track_id", "team", "field_x", "field_y"}
) -> dict | None:
    best = None
    best_dist = MAX_POSSESSION_DISTANCE
    for player in players:
        if player.get("field_x") is None or player.get("field_y") is None:
            continue
        dist = math.hypot(player["field_x"] - ball_field_pos[0], player["field_y"] - ball_field_pos[1])
        if dist < best_dist:
            best_dist = dist
            best = player
    return best


def estimate_possession_split(possession_events: list[str | None]) -> dict[str, float]:
    """`possession_events` is a list of team labels ("home"/"away"/None)
    per sampled frame where possession could be attributed. Returns a
    normalized {"home": x, "away": y} split (ignoring frames with no
    attributable possession)."""
    attributed = [t for t in possession_events if t in ("home", "away")]
    if not attributed:
        return {"home": 0.5, "away": 0.5}
    home_share = attributed.count("home") / len(attributed)
    return {"home": round(home_share, 3), "away": round(1 - home_share, 3)}
