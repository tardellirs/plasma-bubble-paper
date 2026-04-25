"""Live ingest progress (read-only)."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter

from epb_detector.ingest import cache

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/status")
def status() -> dict:
    df = cache.load_manifest()
    if df.empty:
        return {
            "total": 0,
            "ok": 0,
            "failed": 0,
            "skipped": 0,
            "by_station": {},
            "median_duration_s": None,
            "total_minutes": 0.0,
        }
    counts = df["status"].value_counts().to_dict()
    by_station = (
        df.groupby("sta")["status"]
        .value_counts()
        .unstack(fill_value=0)
        .to_dict(orient="index")
    )
    ok_dur = df.loc[df["status"] == "ok", "duration_s"]
    return {
        "total": int(len(df)),
        "ok": int(counts.get("ok", 0)),
        "failed": int(counts.get("failed", 0)),
        "skipped": int(counts.get("skipped", 0)),
        "by_station": {k: {kk: int(vv) for kk, vv in v.items()} for k, v in by_station.items()},
        "median_duration_s": float(ok_dur.median()) if not ok_dur.empty else None,
        "total_minutes": float(ok_dur.sum() / 60.0) if not ok_dur.empty else 0.0,
        "last_completed_at": (
            str(df["completed_at"].max()) if "completed_at" in df.columns else None
        ),
    }


@router.get("/recent")
def recent(limit: int = 20) -> list[dict]:
    df = cache.load_manifest()
    if df.empty:
        return []
    df = df.sort_values("completed_at", ascending=False).head(limit)
    return df.to_dict(orient="records")
