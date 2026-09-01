from app.analytics.events import detect_events_for_snapshot, throttle_events


def test_numerical_advantage_produces_event():
    advantages = [
        {
            "zone": "left_final_third",
            "home_count": 4,
            "away_count": 3,
            "advantage_team": "home",
            "advantage_label": "4v3",
        }
    ]
    events = detect_events_for_snapshot(124.5, {"home": {}, "away": {}}, advantages)
    assert len(events) == 1
    event = events[0]
    assert event["type"] == "numerical_advantage"
    assert event["team"] == "home"
    assert "4v3" in event["description"]
    assert event["source"] == "computer_vision_fact"


def test_excessive_width_and_low_compactness_events():
    team_metrics = {
        "home": {"width": 65.0, "depth": 20.0, "compactness": 0.2},
        "away": {"width": 30.0, "depth": 20.0, "compactness": 0.8},
    }
    events = detect_events_for_snapshot(10.0, team_metrics, [])
    types = {(e["team"], e["type"]) for e in events}
    assert ("home", "excessive_team_width") in types
    assert ("home", "low_compactness") in types
    assert ("away", "excessive_team_width") not in types
    assert ("away", "low_compactness") not in types


def test_throttle_events_drops_rapid_repeats():
    events = [
        {"timestamp": 1.0, "type": "numerical_advantage", "team": "home", "severity": "high", "description": "a", "source": "computer_vision_fact"},
        {"timestamp": 2.0, "type": "numerical_advantage", "team": "home", "severity": "high", "description": "b", "source": "computer_vision_fact"},
        {"timestamp": 15.0, "type": "numerical_advantage", "team": "home", "severity": "high", "description": "c", "source": "computer_vision_fact"},
    ]
    kept = throttle_events(events)
    assert [e["description"] for e in kept] == ["a", "c"]
