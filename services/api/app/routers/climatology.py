"""Climatology aggregations: bubble rate by LT × month, station × month, etc."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from epb_detector.config import SETTINGS

router = APIRouter(prefix="/climatology", tags=["climatology"])


@router.get("/lt-month")
def lt_by_month(
    snapshot_id: str = Query(default="v0"),
    station: str | None = None,
) -> dict:
    snap = SETTINGS.paths.data_snapshots / snapshot_id
    feat_path = snap / "features.parquet"
    label_path = snap / "labels.parquet"
    if not feat_path.exists():
        raise HTTPException(status_code=404, detail=f"Unknown snapshot {snapshot_id!r}")
    con = duckdb.connect()
    where = f"WHERE f.sta = '{station.upper()}'" if station else ""
    try:
        df = con.execute(
            f"""
            SELECT
                CAST(month(f.window_start) AS INT) AS month,
                CAST(FLOOR(f.local_time_mean) AS INT) AS lt_hour,
                AVG(l.label) AS positive_rate,
                COUNT(*) AS n
            FROM parquet_scan('{feat_path}') f
            JOIN parquet_scan('{label_path}') l USING (window_id)
            {where}
            GROUP BY month, lt_hour
            ORDER BY month, lt_hour
            """
        ).df()
    finally:
        con.close()
    return {
        "snapshot_id": snapshot_id,
        "station": station,
        "rows": df.to_dict(orient="records"),
    }
