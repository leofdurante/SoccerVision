"""API endpoint tests.

The upload -> processing -> completed test is a real integration test:
it runs the actual YOLO/ByteTrack/team-classifier/field-mapper/analytics
pipeline against the small synthetic demo video (generated from a real
photo of people, see scripts/generate_demo_video.py), via
`BackgroundTasks`, exactly as production does. It's slower than a unit
test (a few seconds) but is what actually proves the wiring works.
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.database import init_db

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_VIDEO = REPO_ROOT / "data" / "demo_assets" / "demo_match.mp4"


@pytest.fixture(scope="module")
def client():
    init_db()
    from app.main import app

    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "ai_enabled" in body


def test_get_unknown_analysis_returns_404(client):
    response = client.get("/api/v1/analyses/does-not-exist")
    assert response.status_code == 404


def test_upload_rejects_unsupported_file_type(client):
    response = client.post(
        "/api/v1/analyses",
        files={"file": ("clip.mkv", io.BytesIO(b"not a real video"), "video/x-matroska")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/api/v1/analyses",
        files={"file": ("clip.mp4", io.BytesIO(b""), "video/mp4")},
    )
    assert response.status_code == 400


def test_upload_rejects_unreadable_video(client):
    response = client.post(
        "/api/v1/analyses",
        files={"file": ("clip.mp4", io.BytesIO(b"this is not valid mp4 data"), "video/mp4")},
    )
    assert response.status_code == 400


@pytest.mark.skipif(not DEMO_VIDEO.exists(), reason="Demo video not generated — run scripts/generate_demo_video.py")
def test_full_upload_and_analysis_pipeline(client):
    with DEMO_VIDEO.open("rb") as f:
        response = client.post(
            "/api/v1/analyses",
            files={"file": ("demo_match.mp4", f, "video/mp4")},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    analysis_id = body["analysis_id"]

    # TestClient runs BackgroundTasks synchronously as part of request
    # handling, so by the time `.post()` returns above the pipeline has
    # already executed. Status should already reflect that.
    status_response = client.get(f"/api/v1/analyses/{analysis_id}/status")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] in ("completed", "failed")

    full_response = client.get(f"/api/v1/analyses/{analysis_id}")
    assert full_response.status_code == 200
    full_body = full_response.json()
    assert full_body["original_filename"] == "demo_match.mp4"
    assert full_body["video_metadata"] is not None

    metrics_response = client.get(f"/api/v1/analyses/{analysis_id}/metrics")
    assert metrics_response.status_code == 200
    assert "home" in metrics_response.json()

    events_response = client.get(f"/api/v1/analyses/{analysis_id}/events")
    assert events_response.status_code == 200

    players_response = client.get(f"/api/v1/analyses/{analysis_id}/players")
    assert players_response.status_code == 200

    video_response = client.get(f"/api/v1/analyses/{analysis_id}/video")
    assert video_response.status_code == 200
