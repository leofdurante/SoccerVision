"""Pydantic schemas — the API's type-safe contract.

These are intentionally decoupled from the SQLAlchemy models in
`app.models` so the API shape can evolve independently of storage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Team = Literal["home", "away", "unknown"]
AnalysisStatus = Literal["queued", "processing", "completed", "failed"]
Stage = Literal[
    "uploaded",
    "extracting_frames",
    "detecting_players",
    "tracking_players",
    "classifying_teams",
    "mapping_field",
    "calculating_metrics",
    "generating_insights",
    "completed",
    "failed",
]


class AnalysisCreateResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatus


class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    stage: Stage
    progress: int = Field(ge=0, le=100)
    error_message: str | None = None


class VideoMetadata(BaseModel):
    fps: float
    width: int
    height: int
    duration_seconds: float
    frame_count: int
    processing_fps: float
    processed_frame_count: int


class PlayerFrame(BaseModel):
    """One player's tracked state at one sampled timestamp."""

    track_id: int
    timestamp: float
    bbox: list[float] = Field(min_length=4, max_length=4)
    center: list[float] = Field(min_length=2, max_length=2)
    confidence: float
    team: Team
    team_confidence: float
    field_x: float | None = None
    field_y: float | None = None


class BallFrame(BaseModel):
    timestamp: float
    bbox: list[float] = Field(min_length=4, max_length=4)
    center: list[float] = Field(min_length=2, max_length=2)
    confidence: float
    field_x: float | None = None
    field_y: float | None = None
    possession_track_id: int | None = None
    possession_team: Team | None = None


class AnalysisPlayersResponse(BaseModel):
    analysis_id: str
    frames: list[PlayerFrame]
    track_ids: list[int]


class TeamMetrics(BaseModel):
    team: Team
    width: float | None = None
    depth: float | None = None
    centroid: list[float] | None = None
    avg_spacing: float | None = None
    compactness: float | None = None
    defensive_line_height: float | None = None
    formation: str | None = None
    formation_confidence: float | None = None
    formation_is_heuristic: bool = True
    players_in_defensive_third: int = 0
    players_in_middle_third: int = 0
    players_in_final_third: int = 0


class NumericalAdvantage(BaseModel):
    zone: str
    home_count: int
    away_count: int
    advantage_team: Team
    advantage_label: str  # e.g. "4v3"


class MetricsResponse(BaseModel):
    analysis_id: str
    home: TeamMetrics
    away: TeamMetrics
    numerical_advantages: list[NumericalAdvantage]
    possession_estimate: dict[str, float] | None = None  # {"home": 0.55, "away": 0.45} -- ESTIMATED


class TacticalEvent(BaseModel):
    timestamp: float
    type: str
    severity: Literal["low", "medium", "high"]
    team: Team | None = None
    description: str
    source: Literal["computer_vision_fact"] = "computer_vision_fact"


class AnalysisEventsResponse(BaseModel):
    analysis_id: str
    events: list[TacticalEvent]


class TimelineEntry(BaseModel):
    timestamp: float
    label: str
    type: str


class AnalysisTimelineResponse(BaseModel):
    analysis_id: str
    entries: list[TimelineEntry]


class Insight(BaseModel):
    text: str
    based_on: list[str] = Field(default_factory=list)
    source: Literal["ai_interpretation", "rule_based_fallback"]


class AnalysisFullResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    stage: Stage
    progress: int
    original_filename: str
    video_url: str
    annotated_video_url: str | None = None
    video_metadata: VideoMetadata | None = None
    metrics: MetricsResponse | None = None
    events: list[TacticalEvent] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    insights: list[Insight] = Field(default_factory=list)
    players: list[PlayerFrame] = Field(default_factory=list)
    ball_positions: list[BallFrame] = Field(default_factory=list)
    created_at: datetime
    error_message: str | None = None
