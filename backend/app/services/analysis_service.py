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
import math
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.analytics import advantages, events as events_engine, formations, possession, spacing
from app.analytics.zones import x_third
from app.core.config import Settings
from app.cv.field_mapper import FieldMapper
from app.cv.pitch_view import estimate_visible_pitch
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


# A broadcast overlay sits still near the top of frame for the whole match, so
# the person detector finds it every frame and the tracker rewards it with the
# longest, most consistent "player" track in the analysis. Real players move.
# No single one of these signals separates it — a distant player can sit high
# in frame, and a goalkeeper can stand still — but the combination does.
GRAPHIC_MIN_SAMPLES = 50
GRAPHIC_MAX_FEET_FRACTION = 0.25
GRAPHIC_MAX_SPREAD_PX = 120.0

# Keep detections whose mapped feet sit on the pitch, plus a little slack so
# a box that slightly straddles the touchline is not dropped.
_PITCH_MARGIN = 2.0


def _on_pitch(field_x: float, field_y: float, margin: float = _PITCH_MARGIN) -> bool:
    return -margin <= field_x <= 100.0 + margin and -margin <= field_y <= 100.0 + margin


def _player_feet(bbox: list[float]) -> tuple[float, float]:
    """Image-space point used for pitch mapping: bottom-centre of the box."""
    x1, _, x2, y2 = bbox
    return ((x1 + x2) / 2.0, y2)


def _drop_short_tracks(
    trajectories: dict[int, list[dict]], min_samples: int
) -> list[int]:
    """Remove tracks that only flickered for a handful of frames.

    ByteTrack minting a new id on a miss is the usual source of "40 players"
    on an 11-a-side pitch — those fragments never last a full second.
    """
    if min_samples <= 1:
        return []

    removed: list[int] = []
    for track_id, frames in list(trajectories.items()):
        if len(frames) < min_samples:
            del trajectories[track_id]
            removed.append(track_id)
    return removed


def _strip_discarded_tracks(
    per_frame_tracks: list[tuple[float, list]],
    discarded: set[int],
    track_crops: dict[int, list] | None = None,
) -> list[tuple[float, list]]:
    if not discarded:
        return per_frame_tracks
    if track_crops is not None:
        for track_id in discarded:
            track_crops.pop(track_id, None)
    return [
        (ts, [o for o in objects if o.track_id not in discarded])
        for ts, objects in per_frame_tracks
    ]


def _drop_static_overlay_tracks(
    trajectories: dict[int, list[dict]], frame_height: int
) -> list[int]:
    """Remove tracks that behave like on-screen graphics, not players.

    Returns the ids removed, so the caller can log what went.
    """
    if frame_height <= 0:
        return []

    removed: list[int] = []
    for track_id, frames in list(trajectories.items()):
        if len(frames) < GRAPHIC_MIN_SAMPLES:
            continue

        mean_feet = sum(f["bbox"][3] for f in frames) / len(frames)
        if mean_feet / frame_height >= GRAPHIC_MAX_FEET_FRACTION:
            continue

        xs = [f["center"][0] for f in frames]
        ys = [f["center"][1] for f in frames]
        spread = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
        if spread >= GRAPHIC_MAX_SPREAD_PX:
            continue

        del trajectories[track_id]
        removed.append(track_id)

    return removed


def _frame_budget(analysis: Analysis, settings: Settings) -> int:
    """How many sampled frames this analysis is allowed to process.

    With no window, the default cap applies. With an explicit window, the
    request wins up to `max_window_frames` — so naming a passage actually
    gets you that passage instead of its first 60 seconds.
    """
    start = analysis.analysis_start_seconds
    end = analysis.analysis_end_seconds
    if start is None and end is None:
        return settings.max_processed_frames

    if end is None:
        # Open-ended from an offset: keep the larger ceiling, not the default.
        return settings.max_window_frames

    span_seconds = max(0.0, end - (start or 0.0))
    needed = int(span_seconds * settings.processing_fps) + 1
    return min(needed, settings.max_window_frames)


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
        tracker: Tracker = build_tracker(
            settings.model_path,
            settings.confidence_threshold,
            settings.detection_imgsz,
            settings.filter_to_playing_surface,
        )
        tracker.reset()

        field_mapper = FieldMapper()
        last_view_log = ""

        player_trajectory: dict[int, list[dict]] = defaultdict(list)
        ball_trajectory: list[dict] = []
        track_crops: dict[int, list[np.ndarray]] = defaultdict(list)
        per_frame_tracks: list[tuple[float, list]] = []

        _update(db, analysis, stage="tracking_players", progress=15)

        # A coach who names a window expects that window. The default budget
        # only covers 60 seconds at 5 fps, so applying it to an explicit
        # request truncated it silently — a 5:00-7:00 ask returned 5:00-6:00
        # while the UI still called it "the passage you asked for".
        max_frames = _frame_budget(analysis, settings)
        processed_count = 0
        for sampled in processor.extract_frames(
            start_seconds=analysis.analysis_start_seconds or 0.0,
            end_seconds=analysis.analysis_end_seconds,
        ):
            if processed_count >= max_frames:
                logger.warning(
                    "Analysis %s: hit the frame budget of %d, truncating the "
                    "remainder of the requested window",
                    analysis_id,
                    max_frames,
                )
                break

            view = estimate_visible_pitch(sampled.image)
            if view is not None:
                field_mapper.update_visible_view(
                    metadata.width,
                    metadata.height,
                    view.image_corners,
                    view.pitch_corners,
                    label=view.label,
                )
                if view.label != last_view_log:
                    logger.info(
                        "Analysis %s: visible pitch is %s (x=%.0f–%.0f, conf=%.2f)",
                        analysis_id,
                        view.label,
                        view.pitch_corners[0][0],
                        view.pitch_corners[1][0],
                        view.confidence,
                    )
                    last_view_log = view.label
            elif not field_mapper.is_ready:
                field_mapper.calculate_homography(metadata.width, metadata.height)

            tracked_objects = tracker.update(sampled.image)
            kept_objects = []

            for obj in tracked_objects:
                x1, y1, x2, y2 = [max(0, int(v)) for v in obj.bbox]

                if obj.class_name == "player":
                    field_x, field_y = field_mapper.image_to_field(_player_feet(obj.bbox))
                    if not _on_pitch(field_x, field_y):
                        continue
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
                    kept_objects.append(obj)

                    if len(track_crops[obj.track_id]) < CROPS_PER_TRACK and x2 > x1 and y2 > y1:
                        crop = sampled.image[y1:y2, x1:x2].copy()
                        if crop.size > 0:
                            track_crops[obj.track_id].append(crop)

                elif obj.class_name == "ball":
                    field_x, field_y = field_mapper.image_to_field(tuple(obj.center))
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
                    kept_objects.append(obj)

            per_frame_tracks.append((sampled.timestamp, kept_objects))
            processed_count += 1

            if processed_count % 10 == 0:
                progress = 15 + int(25 * processed_count / max_frames)
                _update(db, analysis, progress=min(40, progress))

        min_track_samples = max(4, int(round(settings.processing_fps)))
        short_ids = _drop_short_tracks(player_trajectory, min_track_samples)
        per_frame_tracks = _strip_discarded_tracks(per_frame_tracks, set(short_ids), track_crops)
        if short_ids:
            logger.info(
                "Analysis %s: discarded %d short-lived track(s) shorter than %d "
                "samples — these are almost certainly ByteTrack identity splits",
                analysis_id,
                len(short_ids),
                min_track_samples,
            )

        overlay_ids = _drop_static_overlay_tracks(player_trajectory, metadata.height)
        per_frame_tracks = _strip_discarded_tracks(per_frame_tracks, set(overlay_ids), track_crops)
        if overlay_ids:
            logger.info(
                "Analysis %s: discarded %d static-overlay track(s) %s — these sit "
                "still near the top of frame and are almost certainly broadcast "
                "graphics rather than players",
                analysis_id,
                len(overlay_ids),
                overlay_ids,
            )

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
        # Re-read sampled frames and draw as we write. Holding the 1080p
        # tracking pass in RAM (several GB) is what made a 90s clip look hung
        # after YOLO finished.
        annotated_path = None
        if per_frame_tracks:
            try:
                from app.services.storage import annotated_video_path

                out_path = annotated_video_path(analysis_id)

                def _annotated_frames():
                    for sampled, (_, objects) in zip(
                        processor.extract_frames(
                            start_seconds=analysis.analysis_start_seconds or 0.0,
                            end_seconds=analysis.analysis_end_seconds,
                        ),
                        per_frame_tracks,
                    ):
                        yield _annotate_frame(sampled.image, objects, team_by_track)

                processor.write_frame_stream(
                    out_path, _annotated_frames(), fps=settings.processing_fps
                )
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
            field_x, field_y = field_mapper.image_to_field(_player_feet(obj.bbox))
            if not _on_pitch(field_x, field_y):
                continue
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


def _annotate_frame(
    frame: np.ndarray,
    tracked_objects: list,
    team_by_track: dict[int, dict],
) -> np.ndarray:
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
    return canvas
