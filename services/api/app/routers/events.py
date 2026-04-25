"""Bubble-event catalogue endpoints."""

from __future__ import annotations

from datetime import datetime

import duckdb
from fastapi import APIRouter, Query

from epb_detector.config import SETTINGS

router = APIRouter(prefix="/events", tags=["events"])

EVENT_GLOB = SETTINGS.paths.data_processed / "events" / "*.parquet"


def _query_events(where_sql: str, params: list) -> list[dict]:
    pattern = str(EVENT_GLOB)
    if not list(EVENT_GLOB.parent.glob("*.parquet")):
        return []
    con = duckdb.connect()
    try:
        sql = f"""
            SELECT *
            FROM parquet_scan('{pattern}')
            {where_sql}
            ORDER BY start
            LIMIT 5000
        """
        return con.execute(sql, params).df().to_dict(orient="records")
    finally:
        con.close()


@router.get("")
def list_events(
    station: str | None = Query(default=None, description="Filter by station ID"),
    t0: datetime | None = Query(default=None, description="Earliest event start (UTC)"),
    t1: datetime | None = Query(default=None, description="Latest event start (UTC)"),
    min_prob: float = Query(default=0.5, ge=0.0, le=1.0),
) -> list[dict]:
    clauses: list[str] = ["peak_probability >= ?"]
    params: list = [min_prob]
    if station:
        clauses.append("sta = ?")
        params.append(station.upper())
    if t0:
        clauses.append("start >= ?")
        params.append(t0)
    if t1:
        clauses.append("start <= ?")
        params.append(t1)
    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    return _query_events(where_sql, params)


@router.get("/summary")
def events_summary() -> dict:
    """Aggregate counts useful for the homepage hero."""
    if not list(EVENT_GLOB.parent.glob("*.parquet")):
        return {"total": 0, "by_station": {}}
    con = duckdb.connect()
    try:
        df = con.execute(
            f"SELECT sta, COUNT(*) AS n FROM parquet_scan('{EVENT_GLOB}') GROUP BY sta"
        ).df()
        return {
            "total": int(df["n"].sum()),
            "by_station": dict(zip(df["sta"], df["n"].astype(int), strict=False)),
        }
    finally:
        con.close()
