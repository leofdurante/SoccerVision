# SoccerVision — Implementation Plan

## 0. Repository state at start

The repository was freshly created and empty (only `.git`). No prior code,
config, or `.env` existed to inspect or preserve. This plan is written
against a clean slate.

## 1. Environment findings

| Tool | Status | Decision |
|---|---|---|
| Node.js v26 / npm 11 | present | use for Next.js frontend |
| Python 3.12 | present | use `backend/.venv` virtualenv, never global site-packages |
| Homebrew | present | used to install ffmpeg |
| ffmpeg | installed via `brew install ffmpeg` (8.1.2) | used for metadata/frame extraction alongside OpenCV |
| Internet (PyPI, npm) | reachable | pretrained YOLO weights (`yolov8n.pt`) auto-download from Ultralytics' public release assets on first use |

No secrets were present anywhere. None have been invented.

## 2. Model / config decisions made from public documentation (non-secret)

- **Object detector**: Ultralytics YOLOv8 (`yolov8n.pt`), COCO-pretrained.
  COCO class `0 = person` is mapped to `player`, class `32 = sports ball`
  is mapped to `ball`. This is a well-documented public model; no
  soccer-specific fine-tuned weights are bundled (would require training
  data / a custom hosted checkpoint we don't have credentials for). This
  is called out explicitly in the README as a limitation — COCO has no
  distinct "referee" class, so referees are detected as generic `person`
  and disambiguated downstream (best-effort) by the team classifier
  reporting low confidence / a third color cluster.
- **Tracker**: Ultralytics' built-in ByteTrack (`bytetrack.yaml`), invoked
  via `model.track(..., tracker="bytetrack.yaml")`. This ships inside the
  `ultralytics` package itself — no separate service or extra model
  download needed.
- **AI tactical analyst**: implemented against the Anthropic Messages API
  (`AI_API_BASE_URL=https://api.anthropic.com`, `MODEL_NAME=claude-sonnet-5`
  as the default in `.env.example`), since this is a Claude Code session
  and Anthropic's API is public, documented, and the natural default here.
  `AI_API_KEY` is left blank in `.env.example` — the user must supply
  their own key. The insight generator is written as a small
  provider-agnostic interface (`AIInsightGenerator`) so it degrades to a
  deterministic, rule-based "insight" fallback when no key is configured,
  so the rest of the app is demoable without any external call at all.

## 3. Architecture

```
frontend (Next.js/TS/Tailwind)
   │  REST + polling
   ▼
backend (FastAPI)
   │
   ├─ POST /api/v1/analyses          → create job, store upload
   ├─ background worker (asyncio task) per job
   │     stage: extracting_frames → detecting_players → tracking_players
   │            → classifying_teams → mapping_field → calculating_metrics
   │            → generating_insights → completed
   │
   ├─ app/cv/        detector.py, tracker.py, team_classifier.py, field_mapper.py
   ├─ app/analytics/ formations.py, spacing.py, possession.py, zones.py, advantages.py, events.py
   ├─ app/services/  video_processor.py, analysis_service.py, ai_analyst.py
   ├─ app/models/    SQLAlchemy models (SQLite, swappable to Postgres via DATABASE_URL)
   ├─ app/schemas/   Pydantic request/response schemas
   └─ app/api/       FastAPI routers only — no business logic in handlers
```

Full Mermaid diagram lives in the README.

## 4. Milestone plan (executed in this exact order, app verified runnable after each)

1. Next.js + FastAPI scaffold, `/api/v1/health` round trip from the frontend.
2. Video upload endpoint (`POST /api/v1/analyses`) + upload UI, MP4/MOV/AVI validated with OpenCV.
3. `VideoProcessor`: metadata + configurable-FPS frame extraction, progress stages wired end to end (still fake CV, real pipeline plumbing).
4. `Detector` (YOLOv8) → annotated output video with boxes.
5. `Tracker` (ByteTrack via ultralytics) → persistent track IDs, trajectories stored.
6. `TeamClassifier` (HSV shirt-color clustering, KMeans) → home/away labels + confidence.
7. `FieldMapper` (manual 4-point homography config → `cv2.getPerspectiveTransform`) → normalized pitch coordinates.
8. `analytics/`: width, depth, centroid, spacing, compactness, defensive line, zone occupancy, formation heuristic.
9. `analytics/advantages.py` + `events.py`: zone-vs-zone numerical advantage + rule-based tactical events.
10. Dashboard UI: video player, top-down pitch (SVG) synced to video time, metric cards, timeline.
11. `ai_analyst.py`: structured JSON → Anthropic API (or deterministic fallback) → labeled "AI interpretation" insights, kept separate from CV-fact fields.
12. Polish: error states, empty-state handling, README, demo video instructions.

## 5. What is explicitly out of scope (per spec)

Live/webcam/WebRTC/RTSP ingestion, auth, billing, custom model training,
perfect possession/formation accuracy, production cloud deployment, mobile
apps. None of this is stubbed or scaffolded — it simply doesn't exist in
the codebase.
