"""FastAPI app exposing read-only access to events, predictions, and dataset snapshots."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.api.app.routers import (
    climatology,
    dataset,
    events,
    forecast,
    health,
    ingest,
    stations,
    storms,
    validation,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="EPB Detector API",
        description=(
            "Public, read-only API for the Equatorial Plasma Bubble detector. "
            "Backed by parquet dataset snapshots and an XGBoost classifier."
        ),
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(stations.router)
    app.include_router(events.router)
    app.include_router(dataset.router)
    app.include_router(climatology.router)
    app.include_router(storms.router)
    app.include_router(ingest.router)
    app.include_router(validation.router)
    app.include_router(forecast.router)

    return app


app = create_app()
