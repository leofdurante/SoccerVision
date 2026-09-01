"""SQLAlchemy engine/session setup.

Uses SQLite for the hackathon MVP (`DATABASE_URL=sqlite:///...`). Swapping
to Postgres later is just an env var change — nothing here is SQLite-specific
except the `connect_args` flag needed for SQLite's threading model.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import REPO_ROOT, get_settings

settings = get_settings()


def _resolve_database_url(url: str) -> str:
    """Relative sqlite paths (e.g. `sqlite:///./data/soccervision.db`) are
    resolved against the repo root, not the process's CWD, and their
    parent directory is created up front — SQLite won't create it."""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    raw_path = url[len(prefix) :]
    if raw_path == ":memory:":
        return url
    path = Path(raw_path)
    if not path.is_absolute():
        path = (REPO_ROOT / raw_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"{prefix}{path}"


_resolved_url = _resolve_database_url(settings.database_url)
_connect_args = {"check_same_thread": False} if _resolved_url.startswith("sqlite") else {}

engine = create_engine(_resolved_url, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    # Import models so they're registered on Base.metadata before create_all.
    from app.models import analysis  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
