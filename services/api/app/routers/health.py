"""Health and metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from epb_detector import __version__

router = APIRouter(prefix="", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
