"""ORM model for an analysis job.

The heavy structured results (players, events, metrics, timeline) are
stored as JSON blobs rather than fully normalized tables — appropriate for
a hackathon MVP where the schema is still evolving. Pydantic schemas in
`app.schemas` give type-safe access on top of this at the API boundary.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)

    # Lifecycle
    status: Mapped[str] = mapped_column(String, default="queued")  # queued|processing|completed|failed
    stage: Mapped[str] = mapped_column(String, default="uploaded")
    progress: Mapped[int] = mapped_column(Float, default=0)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    # Source video
    original_filename: Mapped[str] = mapped_column(String)
    video_path: Mapped[str] = mapped_column(String)
    annotated_video_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # Video metadata (populated during frame extraction)
    video_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Pipeline results (populated progressively as stages complete)
    players: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ball_positions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    events: Mapped[list | None] = mapped_column(JSON, nullable=True)
    insights: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
