"""Orchestrates the full analysis pipeline for one uploaded video.

This is the one place that wires together `app.cv.*` and
`app.analytics.*` into the stage sequence described in the spec:

  uploaded -> extracting_frames -> detecting_players -> tracking_players
  -> classifying_teams -> mapping_field -> calculating_metrics
  -> generating_insights -> completed

Runs synchronously (it's CPU-bound: OpenCV + YOLO) and is invoked from a
background worker via `asyncio.to_thread` so it never blocks the event
loop or the HTTP request that created the job (see app.workers.job_runner).
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.analytics import advantages, events as events_engine, formations, possession, spacing
from app.analytics.zones import x_third
from app.core.config import Settings
from app.cv.field_mapper import FieldMapper
from app.cv.team_classifier import TeamClassifier
from app.cv.tracker import Tracker, build_tracker
from app.models.analysis import Analysis
from app.services.ai_analyst import build_insight_generator
from app.services.video_processor import VideoProcessor, VideoReadError

logger = logging.getLogger("soccervision.analysis_service")

CROPS_PER_TRACK = 6
TEAM_COLORS_BGR = {"home": (255, 80, 40), "away": (40, 80, 255), "unknown": (200, 200, 200)}


class AnalysisPipelineError(RuntimeError):
    pass


def _update(db: Session, analysis: Analysis, **fields) -> None:
    for key, value in fields.items():
        setattr(analysis, key, value)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)


def run_analysis(analysis_id: str, db: Session, settings: Settings) -> None:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        logger.error("run_analysis called with unknown analysis_id=%s", analysis_id)
        return

    start_time = time.time()
    logger.info("Analysis %s: starting pipeline for %s", analysis_id, analysis.original_filename)

    try:
        _update(db, analysis, status="processing", stage="extracting_frames", progress=5)
        processor = VideoProcessor(Path(analysis.video_path), processing_fps=settings.processing_fps)
        metadata = processor.get_metadata()

        logger.info(
            "Analysis %s: video metadata fps=%s width=%s height=%s duration=%.1fs frames=%s",
            analysis_id,
            metadata.fps,
            metadata.width,
            metadata.height,
            metadata.duration_seconds,
            metadata.frame_count,
        )

        # --- detecting_players / tracking_players -------------------------
        _update(db, analysis, stage="detecting_players", progress=10)
        tracker: Tracker = build_tracker(settings.model_path, settings.confidence_threshold)
        tracker.reset()

        field_mapper = FieldMapper()
        field_mapper.calculate_homography(metadata.width, metadata.height)

        player_trajectory: dict[int, list[dict]] = defaultdict(list)
        ball_trajectory: list[dict] = []
        track_crops: dict[int, list[np.ndarray]] = defaultdict(list)
        annotated_frames: list[np.ndarray] = []
        per_frame_tracks: list[tuple[float, list[dict]]] = []

        _update(db, analysis, stage="tracking_players", progress=15)

        max_frames = settings.max_processed_frames
        processed_count = 0
        for sampled in processor.extract_frames():
            if processed_count >= max_frames:
                logger.warning(
                    "Analysis %s: reached MAX_PROCESSED_FRAMES=%d, truncating remainder of video",
                    analysis_id,
                    max_frames,
                )
                break

            tracked_objects = tracker.update(sampled.image)
            frame_players = []

            for obj in tracked_objects:
                x1, y1, x2, y2 = [max(0, int(v)) for v in obj.bbox]
                field_x, field_y = field_mapper.image_to_field(tuple(obj.center))

                if obj.class_name == "player":
                    entry = {
                        "track_id": obj.track_id,
                        "timestamp": round(sampled.timestamp, 3),
                        "bbox": obj.bbox,
                        "center": obj.center,
                        "confidence": obj.confidence,
                        "field_x": round(field_x, 2),
                        "field_y": round(field_y, 2),
                    }
                    player_trajectory[obj.track_id].append(entry)
                    frame_players.append(entry)

                    if len(track_crops[obj.track_id]) < CROPS_PER_TRACK and x2 > x1 and y2 > y1:
                        crop = sampled.image[y1:y2, x1:x2].copy()
                        if crop.size > 0:
                            track_crops[obj.track_id].append(crop)

                elif obj.class_name == "ball":
                    ball_trajectory.append(
                        {
                            "timestamp": round(sampled.timestamp, 3),
                            "bbox": obj.bbox,
                            "center": obj.center,
                            "confidence": obj.confidence,
                            "field_x": round(field_x, 2),
                            "field_y": round(field_y, 2),
                        }
                    )

            per_frame_tracks.append((sampled.timestamp, tracked_objects))
            annotated_frames.append(sampled.image)  # team labels drawn in a second pass, once known
            processed_count += 1

            if processed_count % 10 == 0:
                progress = 15 + int(25 * processed_count / max_frames)
                _update(db, analysis, progress=min(40, progress))

        logger.info(
            "Analysis %s: tracked %d unique players, %d ball detections across %d frames",
            analysis_id,
            len(player_trajectory),
            len(ball_trajectory),
            processed_count,
        )

        # --- classifying_teams ---------------------------------------------
        _update(db, analysis, stage="classifying_teams", progress=45)
        team_by_track: dict[int, dict] = {}
        classifier = TeamClassifier()
        all_crops = [crop for crops in track_crops.values() for crop in crops]
        fitted = classifier.fit(all_crops) if all_crops else False

        for track_id, crops in track_crops.items():
            if not fitted or not crops:
                team_by_track[track_id] = {"team": "unknown", "confidence": 0.0}
                continue
            votes: dict[str, list[float]] = defaultdict(list)
            for crop in crops:
                result = classifier.classify(crop)
                votes[result["team"]].append(result["confidence"])
            best_team = max(votes.items(), key=lambda kv: len(kv[1]))
            team_by_track[track_id] = {
                "team": best_team[0],
                "confidence": round(sum(best_team[1]) / len(best_team[1]), 3),
            }

        for track_id, frames in player_trajectory.items():
            team_info = team_by_track.get(track_id, {"team": "unknown", "confidence": 0.0})
            for frame in frames:
                frame["team"] = team_info["team"]
                frame["team_confidence"] = team_info["confidence"]

        # --- mapping_field ---------------------------------------------------
        # (Homography was already applied above during the tracking pass;
        # this stage is kept explicit per spec for UI/progress visibility.)
        _update(db, analysis, stage="mapping_field", progress=55)

        # --- calculating_metrics ----------------------------------------------
        _update(db, analysis, stage="calculating_metrics", progress=65)

        snapshots = _build_snapshots(per_frame_tracks, team_by_track, field_mapper)
        team_metrics, numerical_advantages_current, all_events = _compute_metrics_and_events(snapshots)

        possession_events = []
        for ts, players_by_id in snapshots:
            ball_at_ts = min(ball_trajectory, key=lambda b: abs(b["timestamp"] - ts), default=None)
            if ball_at_ts is None or abs(ball_at_ts["timestamp"] - ts) > 1.0:
                possession_events.append(None)
                continue
            nearest = possession.nearest_player_to_ball(
                (ball_at_ts["field_x"], ball_at_ts["field_y"]),
                list(players_by_id.values()),
            )
            possession_events.append(nearest["team"] if nearest else None)

        possession_split = possession.estimate_possession_split(possession_events)

        metrics_payload = {
            "home": team_metrics["home"],
            "away": team_metrics["away"],
            "numerical_advantages": numerical_advantages_current,
            "possession_estimate": possession_split,
        }

        # --- generating_insights ------------------------------------------------
        _update(db, analysis, stage="generating_insights", progress=85)
        generator = build_insight_generator(settings)
        structured_stats = {
            "home": team_metrics["home"],
            "away": team_metrics["away"],
            "numerical_advantages": numerical_advantages_current,
        }
        insights = generator.generate(structured_stats)

        # --- annotated output video -----------------------------------------------
        annotated_path = None
        if annotated_frames:
            try:
                drawn = _draw_annotations(annotated_frames, per_frame_tracks, team_by_track)
                from app.services.storage import annotated_video_path

                out_path = annotated_video_path(analysis_id)
                processor.create_output_video(out_path, drawn, fps=settings.processing_fps)
                annotated_path = str(out_path)
            except Exception:
                logger.exception("Analysis %s: failed to write annotated video (non-fatal)", analysis_id)

        timeline = [
            {"timestamp": e["timestamp"], "label": e["description"], "type": e["type"]} for e in all_events
        ]

        video_metadata = {
            "fps": metadata.fps,
            "width": metadata.width,
            "height": metadata.height,
            "duration_seconds": round(metadata.duration_seconds, 2),
            "frame_count": metadata.frame_count,
            "processing_fps": settings.processing_fps,
            "processed_frame_count": processed_count,
        }

        _update(
            db,
            analysis,
            status="completed",
            stage="completed",
            progress=100,
            video_metadata=video_metadata,
            annotated_video_path=annotated_path,
            players=[frame for frames in player_trajectory.values() for frame in frames],
            ball_positions=ball_trajectory,
            metrics=metrics_payload,
            events=all_events,
            insights=insights,
        )
        db.commit()

        duration = time.time() - start_time
        logger.info("Analysis %s: completed in %.1fs", analysis_id, duration)

    except VideoReadError as exc:
        logger.exception("Analysis %s: video read error", analysis_id)
        _update(db, analysis, status="failed", stage="failed", error_message=str(exc))
    except Exception as exc:  # noqa: BLE001 — top-level pipeline guard
        logger.exception("Analysis %s: pipeline failed", analysis_id)
        _update(db, analysis, status="failed", stage="failed", error_message=f"Processing failed: {exc}")


def _build_snapshots(
    per_frame_tracks: list[tuple[float, list]],
    team_by_track: dict[int, dict],
    field_mapper: FieldMapper,
) -> list[tuple[float, dict]]:
    """One snapshot per sampled frame: {track_id: {team, field_x, field_y}}."""
    snapshots = []
    for timestamp, tracked_objects in per_frame_tracks:
        players_by_id = {}
        for obj in tracked_objects:
            if obj.class_name != "player":
                continue
            field_x, field_y = field_mapper.image_to_field(tuple(obj.center))
            team_info = team_by_track.get(obj.track_id, {"team": "unknown", "confidence": 0.0})
            players_by_id[obj.track_id] = {
                "track_id": obj.track_id,
                "team": team_info["team"],
                "field_x": round(field_x, 2),
                "field_y": round(field_y, 2),
            }
        snapshots.append((timestamp, players_by_id))
    return snapshots


def _compute_metrics_and_events(snapshots: list[tuple[float, dict]]):
    raw_events: list[dict] = []
    best_snapshot: tuple[float, dict] | None = None
    best_count = -1

    per_team_running: dict[str, dict[str, list[float]]] = {
        "home": {"width": [], "depth": [], "compactness": [], "defensive_line_height": []},
        "away": {"width": [], "depth": [], "compactness": [], "defensive_line_height": []},
    }

    for timestamp, players_by_id in snapshots:
        by_team: dict[str, list[tuple[float, float]]] = {"home": [], "away": []}
        for p in players_by_id.values():
            if p["team"] in ("home", "away"):
                by_team[p["team"]].append((p["field_x"], p["field_y"]))

        snapshot_metrics = {}
        for team, positions in by_team.items():
            snapshot_metrics[team] = {
                "width": spacing.team_width(positions),
                "depth": spacing.team_depth(positions),
                "compactness": spacing.compactness(positions),
                "defensive_line_height": spacing.defensive_line_height(positions, team),
            }
            for key in ("width", "depth", "compactness", "defensive_line_height"):
                value = snapshot_metrics[team][key]
                if value is not None:
                    per_team_running[team][key].append(value)

        zone_advantages = advantages.find_numerical_advantages(by_team["home"], by_team["away"])
        raw_events.extend(events_engine.detect_events_for_snapshot(timestamp, snapshot_metrics, zone_advantages))

        total_players = len(by_team["home"]) + len(by_team["away"])
        if total_players > best_count:
            best_count = total_players
            best_snapshot = (timestamp, players_by_id, by_team)

    team_metrics = {}
    for team in ("home", "away"):
        avg = {
            key: (round(sum(vals) / len(vals), 2) if vals else None)
            for key, vals in per_team_running[team].items()
        }
        best_positions = best_snapshot[2][team] if best_snapshot else []
        formation_result = formations.estimate_formation(best_positions, team)
        centroid = spacing.team_centroid(best_positions)
        third_counts = spacing.count_in_thirds([(pos, team) for pos in best_positions])

        team_metrics[team] = {
            "team": team,
            "width": avg["width"],
            "depth": avg["depth"],
            "centroid": list(centroid) if centroid else None,
            "avg_spacing": round(spacing.average_spacing(best_positions), 2) if len(best_positions) >= 2 else None,
            "compactness": avg["compactness"],
            "defensive_line_height": avg["defensive_line_height"],
            "formation": formation_result["formation"],
            "formation_confidence": formation_result["confidence"],
            "formation_is_heuristic": True,
            "players_in_defensive_third": third_counts["defensive_third"],
            "players_in_middle_third": third_counts["middle_third"],
            "players_in_final_third": third_counts["final_third"],
        }

    current_advantages = (
        advantages.find_numerical_advantages(best_snapshot[2]["home"], best_snapshot[2]["away"])
        if best_snapshot
        else []
    )

    throttled_events = events_engine.throttle_events(raw_events)
    return team_metrics, current_advantages, throttled_events


def _draw_annotations(
    frames: list[np.ndarray],
    per_frame_tracks: list[tuple[float, list]],
    team_by_track: dict[int, dict],
) -> list[np.ndarray]:
    drawn = []
    for frame, (_, tracked_objects) in zip(frames, per_frame_tracks):
        canvas = frame.copy()
        for obj in tracked_objects:
            x1, y1, x2, y2 = [int(v) for v in obj.bbox]
            if obj.class_name == "ball":
                color = (0, 255, 255)
                label = "ball"
            else:
                team = team_by_track.get(obj.track_id, {}).get("team", "unknown")
                color = TEAM_COLORS_BGR.get(team, TEAM_COLORS_BGR["unknown"])
                label = f"#{obj.track_id} {team}"
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
            cv2.putText(canvas, label, (x1, max(0, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        drawn.append(canvas)
    return drawn
