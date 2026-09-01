"""Rule-based tactical event engine.

Operates purely on structured analytics snapshots (never raw video), per
spec. A "snapshot" is one instant's worth of computed team metrics +
numerical advantages, taken at a sampled timestamp. Thresholds below are
simple, documented heuristics, not tuned against real match data — this
is a hackathon MVP demonstrating the mechanism, not claiming tactical
authority.
"""

from __future__ import annotations

# Thresholds (normalized pitch is 100x100 units)
EXCESSIVE_WIDTH_THRESHOLD = 60.0
EXCESSIVE_DEPTH_THRESHOLD = 55.0
LOW_COMPACTNESS_THRESHOLD = 0.35
ISOLATED_DEFENDER_DISTANCE = 30.0

# Throttle: don't repeat the same (team, type) event more often than this
# many seconds apart, so a sustained condition doesn't spam the timeline.
MIN_EVENT_GAP_SECONDS = 8.0


def _make_event(timestamp: float, event_type: str, severity: str, team: str | None, description: str) -> dict:
    return {
        "timestamp": round(timestamp, 2),
        "type": event_type,
        "severity": severity,
        "team": team,
        "description": description,
        "source": "computer_vision_fact",
    }


def detect_events_for_snapshot(
    timestamp: float,
    team_metrics: dict[str, dict],  # {"home": {...}, "away": {...}} from spacing.py outputs
    numerical_advantages: list[dict],
) -> list[dict]:
    events: list[dict] = []

    for advantage in numerical_advantages:
        events.append(
            _make_event(
                timestamp,
                "numerical_advantage",
                severity="high" if int(advantage["advantage_label"].split("v")[0]) - int(advantage["advantage_label"].split("v")[1]) >= 2 else "medium",
                team=advantage["advantage_team"],
                description=(
                    f"{advantage['advantage_team'].title()} team has a "
                    f"{advantage['advantage_label']} numerical advantage in the "
                    f"{advantage['zone'].replace('_', ' ')}."
                ),
            )
        )

    for team, metrics in team_metrics.items():
        width = metrics.get("width")
        depth = metrics.get("depth")
        comp = metrics.get("compactness")

        if width is not None and width >= EXCESSIVE_WIDTH_THRESHOLD:
            events.append(
                _make_event(
                    timestamp,
                    "excessive_team_width",
                    severity="medium",
                    team=team,
                    description=f"{team.title()} team shape is very wide ({width:.1f} pitch units side to side).",
                )
            )

        if depth is not None and depth >= EXCESSIVE_DEPTH_THRESHOLD:
            events.append(
                _make_event(
                    timestamp,
                    "excessive_team_depth",
                    severity="medium",
                    team=team,
                    description=f"{team.title()} team is very stretched vertically ({depth:.1f} pitch units).",
                )
            )

        if comp is not None and comp <= LOW_COMPACTNESS_THRESHOLD:
            events.append(
                _make_event(
                    timestamp,
                    "low_compactness",
                    severity="low",
                    team=team,
                    description=f"{team.title()} team is loosely grouped (compactness {comp:.2f}), opening central space.",
                )
            )

    return events


def throttle_events(events: list[dict]) -> list[dict]:
    """Drop repeated (team, type) events that occur within
    MIN_EVENT_GAP_SECONDS of a previously kept one, to keep the timeline
    readable."""
    kept: list[dict] = []
    last_seen: dict[tuple[str | None, str], float] = {}
    for event in sorted(events, key=lambda e: e["timestamp"]):
        key = (event.get("team"), event["type"])
        last = last_seen.get(key)
        if last is not None and event["timestamp"] - last < MIN_EVENT_GAP_SECONDS:
            continue
        last_seen[key] = event["timestamp"]
        kept.append(event)
    return kept
