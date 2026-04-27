"""Bubble-event catalogue endpoints."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import duckdb
from fastapi import APIRouter, Query

from epb_detector.config import SETTINGS

router = APIRouter(prefix="/events", tags=["events"])

EVENT_GLOB = SETTINGS.paths.data_processed / "events" / "*.parquet"

ROTI_ROOT = SETTINGS.paths.pyoasis_output / "RINEX"


@lru_cache(maxsize=1)
def _roti_station_days_cached(_mtime_key: float) -> set[tuple[str, int, int]]:
    """Return the set of (sta, year, doy) for which a ROTI.txt file exists.

    The map's event drawer reads raw per-sample ROTI from
    ``OUTPUT/RINEX/<year>/<doy>/<sta>/<sta>_<doy>_<year>_{G,R}_ROTI.txt``.
    Storm-stratified ingest produced predictions for years 2014–2025 but
    only 2023–2024 OUTPUT was synced back to this host, so events
    outside that range come back with 'No raw ROTI file on disk'. We
    pre-compute the available set once and filter /events against it.

    Cache key is the OUTPUT/RINEX root mtime — invalidates whenever a
    new station-day is rsynced in.
    """
    available: set[tuple[str, int, int]] = set()
    if not ROTI_ROOT.exists():
        return available
    for year_dir in ROTI_ROOT.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        for doy_dir in year_dir.iterdir():
            if not doy_dir.is_dir() or not doy_dir.name.isdigit():
                continue
            doy = int(doy_dir.name)
            for sta_dir in doy_dir.iterdir():
                if not sta_dir.is_dir():
                    continue
                sta = sta_dir.name.upper()
                # Has at least one of GPS / GLONASS ROTI on disk.
                if any(
                    (sta_dir / f"{sta}_{doy:03d}_{year}_{sys}_ROTI.txt").exists()
                    for sys in ("G", "R")
                ):
                    available.add((sta, year, doy))
    return available


def _roti_station_days() -> set[tuple[str, int, int]]:
    if not ROTI_ROOT.exists():
        return set()
    # Use the directory mtime as the cache key — rsync of new years/doys
    # bumps it.
    return _roti_station_days_cached(ROTI_ROOT.stat().st_mtime)


def _filter_to_roti_days(rows: list[dict]) -> list[dict]:
    """Drop events whose (sta, year, doy) has no ROTI .txt on disk."""
    available = _roti_station_days()
    if not available:
        return rows
    out: list[dict] = []
    for r in rows:
        start = r.get("start")
        sta = (r.get("sta") or "").upper()
        if start is None or not sta:
            continue
        # `start` arrives as pandas Timestamp from DuckDB.df().
        ts = start if hasattr(start, "year") else datetime.fromisoformat(str(start))
        key = (sta, ts.year, ts.timetuple().tm_yday)
        if key in available:
            out.append(r)
    return out


def _query_events(where_sql: str, params: list, limit: int) -> list[dict]:
    pattern = str(EVENT_GLOB)
    if not list(EVENT_GLOB.parent.glob("*.parquet")):
        return []
    con = duckdb.connect()
    try:
        # The events folder may carry multiple snapshot versions
        # (events_v2.parquet for Phase 2-A, events_v3.parquet for the
        # storm-stratified ingest). They overlap on the days that fell
        # in both selectors. Dedup by (sta, sat, start) and keep the
        # highest-probability row so we don't double-count.
        sql = f"""
            SELECT *
            FROM parquet_scan('{pattern}')
            {where_sql}
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY sta, sat, start
                ORDER BY peak_probability DESC
            ) = 1
            ORDER BY start
            LIMIT {int(limit)}
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
    limit: int = Query(default=50_000, ge=1, le=200_000),
    roti_only: bool = Query(
        default=True,
        description=(
            "Only return events whose station-day has a raw ROTI.txt on "
            "disk. Defaults true so the map drawer's per-sample chart "
            "always has data; pass false to see all model predictions."
        ),
    ),
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
    rows = _query_events(where_sql, params, limit)
    if roti_only:
        rows = _filter_to_roti_days(rows)
    return rows


@router.get("/summary")
def events_summary(roti_only: bool = Query(default=True)) -> dict:
    """Aggregate counts useful for the homepage hero.

    Mirrors /events defaults: dedupes across v2/v3 parquets and (by
    default) only counts events whose station-day has a raw ROTI on
    disk so the home-page total matches what the map actually plots.
    """
    if not list(EVENT_GLOB.parent.glob("*.parquet")):
        return {"total": 0, "by_station": {}}
    con = duckdb.connect()
    try:
        rows = con.execute(
            f"""
            SELECT sta, sat, start, peak_probability
            FROM parquet_scan('{EVENT_GLOB}')
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY sta, sat, start
                ORDER BY peak_probability DESC
            ) = 1
            """
        ).df().to_dict(orient="records")
    finally:
        con.close()
    if roti_only:
        rows = _filter_to_roti_days(rows)
    by_sta: dict[str, int] = {}
    for r in rows:
        by_sta[r["sta"]] = by_sta.get(r["sta"], 0) + 1
    return {"total": sum(by_sta.values()), "by_station": by_sta}


_PRED_PATTERN = SETTINGS.paths.data_processed / "predictions_v*.parquet"


@router.get("/timeseries")
def event_timeseries(
    sta: str = Query(..., description="Station code, e.g. SALU"),
    sat: str = Query(..., description="Satellite, e.g. R03"),
    t0: datetime = Query(..., description="Window start (UTC)"),
    t1: datetime = Query(..., description="Window end (UTC)"),
) -> dict:
    """Per-window time series for one (station, satellite) pair.

    Pulls from the latest ``predictions_v*.parquet`` so the chart in the
    map's event detail panel can show ROTI / ΔTEC / SIDX / model probability
    side by side. Time range is bounded — typical caller pads ±30 minutes
    around an event.
    """
    candidates = sorted(_PRED_PATTERN.parent.glob("predictions_v*.parquet"))
    if not candidates:
        return {"rows": []}
    pattern = str(candidates[-1])
    con = duckdb.connect()
    try:
        df = con.execute(
            f"""
            SELECT window_start AS time,
                   epb_probability AS prob,
                   roti_max,
                   dtec_max,
                   sidx_max,
                   label,
                   kp,
                   dst,
                   storm_phase
            FROM parquet_scan('{pattern}')
            WHERE sta = ?
              AND sat = ?
              AND window_start >= ?
              AND window_start <= ?
            ORDER BY window_start
            """,
            [sta.upper(), sat.upper(), t0, t1],
        ).df()
    finally:
        con.close()
    rows = df.to_dict(orient="records")
    for r in rows:
        if r.get("time") is not None:
            r["time"] = r["time"].isoformat()
    return {"sta": sta.upper(), "sat": sat.upper(), "rows": rows}


@router.get("/day-roti")
def event_day_roti(
    sta: str = Query(..., description="Station code, e.g. SALU"),
    date: datetime = Query(..., description="Day to fetch (UTC, anything in the day works)"),
) -> dict:
    """Raw per-sample ROTI scatter for one station-day.

    Reads the pyOASIS ``<STA>_<DOY>_<YEAR>_{G|R}_ROTI.txt`` files directly so
    the map's event drawer can show the same time-domain scatter that
    ``ROTI_CALC.py`` plots — GPS in one series, GLONASS in another, no
    smoothing or windowing applied. Used in concert with /events/timeseries
    (which gives the per-10-min window probability on top).
    """
    import pandas as pd

    sta_u = sta.upper()
    yr = date.year
    doy = date.timetuple().tm_yday
    base = (
        SETTINGS.paths.pyoasis_output
        / "RINEX"
        / str(yr)
        / f"{doy:03d}"
        / sta_u
    )
    points: list[dict] = []
    for system, label in (("G", "GPS"), ("R", "GLONASS")):
        path = base / f"{sta_u}_{doy:03d}_{yr}_{system}_ROTI.txt"
        if not path.exists():
            continue
        df = pd.read_csv(path, sep=r"\s+")
        if df.empty:
            continue
        # MJD → UNIX seconds (MJD 40587 == 1970-01-01 UTC).
        ts = pd.to_datetime((df["MJD"] - 40587) * 86400, unit="s", utc=True)
        for t, sat, roti in zip(ts, df["SAT"], df["ROTI"], strict=False):
            points.append(
                {
                    "time": t.isoformat(),
                    "sat": str(sat),
                    "system": system,
                    "system_label": label,
                    "roti": float(roti),
                }
            )
    return {
        "sta": sta_u,
        "date": date.date().isoformat(),
        "year": yr,
        "doy": doy,
        "n_points": len(points),
        "points": points,
    }
