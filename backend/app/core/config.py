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
    confidence_threshold: float = 0.4

    # Hackathon-scale safety cap: max sampled frames actually processed
    # per video, to keep demo processing time and memory bounded
    # regardless of how long the uploaded match video is.
    max_processed_frames: int = 300

    # --- AI tactical analyst ---
    ai_api_key: str = ""
    ai_api_base_url: str = "https://api.anthropic.com"
    model_name: str = "claude-sonnet-5"

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
