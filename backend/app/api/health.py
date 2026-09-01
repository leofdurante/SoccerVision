"""Simple liveness/config-visibility endpoint used to confirm the
frontend and backend can talk to each other (Milestone 1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "service": "soccervision-backend",
        "ai_enabled": settings.ai_enabled,
    }
