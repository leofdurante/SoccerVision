"""Local filesystem storage for uploaded/processed video.

Deliberately narrow interface so a later swap to S3 / Azure Blob Storage
only requires a new implementation of this module, not changes to
callers. Nothing here assumes a local filesystem outside this file.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import get_settings

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB — generous for a hackathon demo clip


class UnsupportedVideoError(ValueError):
    pass


def validate_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise UnsupportedVideoError(
            f"Unsupported file type '{suffix}'. Supported formats: "
            f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return suffix


def upload_video_path(analysis_id: str, suffix: str) -> Path:
    settings = get_settings()
    return settings.upload_path / f"{analysis_id}{suffix}"


def annotated_video_path(analysis_id: str) -> Path:
    settings = get_settings()
    return settings.output_path / f"{analysis_id}_annotated.mp4"


def save_upload_stream(destination: Path, tmp_file) -> int:
    """Copy an already-buffered upload to its final location. Returns byte count."""
    with destination.open("wb") as out:
        shutil.copyfileobj(tmp_file, out)
    return destination.stat().st_size
