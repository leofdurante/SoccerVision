"""FastAPI application entrypoint.

Route handlers live in `app.api.*` and contain no business logic — they
delegate to `app.services.*`. This module only wires up the app, CORS,
logging, and routers.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyses, health
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.models.database import init_db

configure_logging()
logger = logging.getLogger("soccervision")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info(
        "SoccerVision backend started | upload_dir=%s output_dir=%s ai_enabled=%s",
        settings.upload_path,
        settings.output_path,
        settings.ai_enabled,
    )
    yield


app = FastAPI(
    title="SoccerVision API",
    description="Upload-based soccer match video analysis: detection, tracking, "
    "team classification, field mapping, tactical analytics, and AI insights.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(analyses.router, prefix="/api/v1")
