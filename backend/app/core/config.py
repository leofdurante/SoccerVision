"""Central application configuration.

All runtime configuration is read from environment variables (with a
`.env` file at the repo root loaded for local development). Nothing here
should ever hold a default that looks like a real secret — `AI_API_KEY`
defaults to empty and the app is expected to behave sensibly when it is.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is three levels up from this file: backend/app/core/config.py
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Storage ---
    database_url: str = "sqlite:///./data/soccervision.db"
    upload_dir: str = "./data/uploads"
    output_dir: str = "./data/processed"

    # --- Computer vision ---
    model_path: str = "yolov8n.pt"
    processing_fps: float = 5.0
    confidence_threshold: float = 0.45

    # Inference resolution. 1280 roughly triples runtime vs 640. 640 is the
    # default so a 90-second 1080p clip finishes in a couple of minutes on
    # CPU; raise it if far-side players are being missed.
    # Measured on real match footage with yolov8n:
    #   640/0.40 -> 6.0 players/frame   1280/0.40 -> 8.5
    #   640/0.25 -> 8.2                 1280/0.25 -> 12.3
    detection_imgsz: int = 640

    # Reject detections whose feet are not on the playing surface. A stadium
    # shot contains substitutes, coaches, officials and spectators, plus the
    # broadcast scorebug, all of which the person detector happily returns.
    filter_to_playing_surface: bool = True

    # Safety cap for an upload with no explicit window: bounds processing
    # time and memory regardless of how long the video is. At 5 fps this is
    # 60 seconds of footage.
    max_processed_frames: int = 300

    # When a coach names a window, that request is honoured up to this
    # larger ceiling rather than being silently cut back to the default
    # budget. At 5 fps this is 10 minutes of footage.
    max_window_frames: int = 3000

    # --- AI tactical analyst ---
    ai_api_key: str = ""
    ai_api_base_url: str = "https://api.anthropic.com"
    model_name: str = "claude-opus-5"

    # Identity-linked API keys must name the workspace the request acts in,
    # or the Messages API rejects the call with a 400. Organization-scoped
    # keys ignore this, so it stays optional.
    ai_workspace_id: str = ""

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        path = (REPO_ROOT / self.upload_dir).resolve() if not Path(self.upload_dir).is_absolute() else Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def output_path(self) -> Path:
        path = (REPO_ROOT / self.output_dir).resolve() if not Path(self.output_dir).is_absolute() else Path(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
