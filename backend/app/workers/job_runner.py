"""Background job execution.

For the local MVP, a background task (via FastAPI's `BackgroundTasks`,
run after the HTTP response is sent) is the "worker/task queue"
abstraction called for in the spec — no external broker required. The
CPU-bound pipeline itself runs in a thread (`asyncio.to_thread`) so it
never blocks the event loop, keeping the API responsive to status polls
while a video processes.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.models.database import SessionLocal
from app.services.analysis_service import run_analysis

logger = logging.getLogger("soccervision.job_runner")


async def process_analysis_job(analysis_id: str) -> None:
    db = SessionLocal()
    try:
        await asyncio.to_thread(run_analysis, analysis_id, db, get_settings())
    except Exception:
        logger.exception("Analysis %s: background job crashed unexpectedly", analysis_id)
    finally:
        db.close()
