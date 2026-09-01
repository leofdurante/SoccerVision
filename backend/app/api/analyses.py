"""Analysis REST endpoints.

Thin controllers only — all business logic lives in `app.services` /
`app.models`. The frontend never needs to know YOLO or ByteTrack exist.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.analysis import Analysis
from app.models.database import get_db
from app.schemas.analysis import (
    AnalysisCreateResponse,
    AnalysisEventsResponse,
    AnalysisFullResponse,
    AnalysisPlayersResponse,
    AnalysisStatusResponse,
    AnalysisTimelineResponse,
    MetricsResponse,
    TeamMetrics,
)
from app.services.storage import (
    UnsupportedVideoError,
    save_upload_stream,
    upload_video_path,
    validate_filename,
)
from app.services.video_processor import VideoProcessor, VideoReadError
from app.workers.job_runner import process_analysis_job

logger = logging.getLogger("soccervision.api.analyses")
router = APIRouter(prefix="/analyses", tags=["analyses"])


def _get_or_404(db: Session, analysis_id: str) -> Analysis:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found")
    return analysis


@router.post("", response_model=AnalysisCreateResponse, status_code=202)
async def create_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AnalysisCreateResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    try:
        suffix = validate_filename(file.filename)
    except UnsupportedVideoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    analysis = Analysis(
        original_filename=file.filename,
        video_path="",  # filled in below once we know the generated id
        status="queued",
        stage="uploaded",
        progress=0,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    destination = upload_video_path(analysis.id, suffix)
    size_bytes = save_upload_stream(destination, file.file)
    if size_bytes == 0:
        db.delete(analysis)
        db.commit()
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    analysis.video_path = str(destination)
    db.add(analysis)
    db.commit()

    # Validate the video is actually readable before queuing the heavy
    # pipeline, so obviously-broken uploads fail fast with a clear error.
    try:
        VideoProcessor(destination).get_metadata()
    except VideoReadError as exc:
        analysis.status = "failed"
        analysis.stage = "failed"
        analysis.error_message = str(exc)
        db.add(analysis)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("Analysis %s created for upload '%s' (%d bytes)", analysis.id, file.filename, size_bytes)

    background_tasks.add_task(process_analysis_job, analysis.id)

    return AnalysisCreateResponse(analysis_id=analysis.id, status="queued")


@router.get("/{analysis_id}", response_model=AnalysisFullResponse)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisFullResponse:
    analysis = _get_or_404(db, analysis_id)

    metrics = None
    if analysis.metrics:
        metrics = MetricsResponse(
            analysis_id=analysis.id,
            home=TeamMetrics(**analysis.metrics["home"]),
            away=TeamMetrics(**analysis.metrics["away"]),
            numerical_advantages=analysis.metrics.get("numerical_advantages", []),
            possession_estimate=analysis.metrics.get("possession_estimate"),
        )

    timeline = [
        {"timestamp": e["timestamp"], "label": e["description"], "type": e["type"]}
        for e in (analysis.events or [])
    ]

    return AnalysisFullResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        stage=analysis.stage,
        progress=int(analysis.progress),
        original_filename=analysis.original_filename,
        video_url=f"/api/v1/analyses/{analysis.id}/video",
        annotated_video_url=(
            f"/api/v1/analyses/{analysis.id}/video/annotated" if analysis.annotated_video_path else None
        ),
        video_metadata=analysis.video_metadata,
        metrics=metrics,
        events=analysis.events or [],
        timeline=timeline,
        insights=analysis.insights or [],
        players=analysis.players or [],
        ball_positions=analysis.ball_positions or [],
        created_at=analysis.created_at,
        error_message=analysis.error_message,
    )


@router.get("/{analysis_id}/video")
def get_video(analysis_id: str, db: Session = Depends(get_db)) -> FileResponse:
    analysis = _get_or_404(db, analysis_id)
    if not analysis.video_path:
        raise HTTPException(status_code=404, detail="Video not found.")
    return FileResponse(analysis.video_path, media_type="video/mp4")


@router.get("/{analysis_id}/video/annotated")
def get_annotated_video(analysis_id: str, db: Session = Depends(get_db)) -> FileResponse:
    analysis = _get_or_404(db, analysis_id)
    if not analysis.annotated_video_path:
        raise HTTPException(status_code=404, detail="Annotated video not available for this analysis.")
    return FileResponse(analysis.annotated_video_path, media_type="video/mp4")


@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_status(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisStatusResponse:
    analysis = _get_or_404(db, analysis_id)
    return AnalysisStatusResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        stage=analysis.stage,
        progress=int(analysis.progress),
        error_message=analysis.error_message,
    )


@router.get("/{analysis_id}/players", response_model=AnalysisPlayersResponse)
def get_players(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisPlayersResponse:
    analysis = _get_or_404(db, analysis_id)
    frames = analysis.players or []
    track_ids = sorted({f["track_id"] for f in frames})
    return AnalysisPlayersResponse(analysis_id=analysis.id, frames=frames, track_ids=track_ids)


@router.get("/{analysis_id}/events", response_model=AnalysisEventsResponse)
def get_events(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisEventsResponse:
    analysis = _get_or_404(db, analysis_id)
    return AnalysisEventsResponse(analysis_id=analysis.id, events=analysis.events or [])


@router.get("/{analysis_id}/metrics", response_model=MetricsResponse)
def get_metrics(analysis_id: str, db: Session = Depends(get_db)) -> MetricsResponse:
    analysis = _get_or_404(db, analysis_id)
    if not analysis.metrics:
        raise HTTPException(status_code=404, detail="Metrics not yet available for this analysis.")
    return MetricsResponse(
        analysis_id=analysis.id,
        home=TeamMetrics(**analysis.metrics["home"]),
        away=TeamMetrics(**analysis.metrics["away"]),
        numerical_advantages=analysis.metrics.get("numerical_advantages", []),
        possession_estimate=analysis.metrics.get("possession_estimate"),
    )


@router.get("/{analysis_id}/timeline", response_model=AnalysisTimelineResponse)
def get_timeline(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisTimelineResponse:
    analysis = _get_or_404(db, analysis_id)
    entries = [
        {"timestamp": e["timestamp"], "label": e["description"], "type": e["type"]}
        for e in (analysis.events or [])
    ]
    return AnalysisTimelineResponse(analysis_id=analysis.id, entries=entries)
