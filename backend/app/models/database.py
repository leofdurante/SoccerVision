"""SQLAlchemy engine/session setup.

Uses SQLite for the hackathon MVP (`DATABASE_URL=sqlite:///...`). Swapping
to Postgres later is just an env var change — nothing here is SQLite-specific
except the `connect_args` flag needed for SQLite's threading model.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import REPO_ROOT, get_settings

logger = logging.getLogger("soccervision.database")

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
    _add_missing_columns()


def _add_missing_columns() -> None:
    """Add columns that `create_all` cannot: it creates missing *tables*,
    but never alters one that already exists, so a new model field would
    otherwise break every existing row on an already-populated database.

    This project has no migration tool, so bridge the gap with an
    idempotent ALTER for the handful of nullable columns added after the
    first release. Anything structural still needs a real migration.
    """
    from sqlalchemy import inspect, text

    expected = {
        "analyses": {
            "analysis_start_seconds": "FLOAT",
            "analysis_end_seconds": "FLOAT",
        },
    }

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table, columns in expected.items():
            if table not in existing_tables:
                continue
            present = {col["name"] for col in inspector.get_columns(table)}
            for name, sql_type in columns.items():
                if name in present:
                    continue
                logger.info("Adding missing column %s.%s", table, name)
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
