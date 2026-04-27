"""Geomagnetic-storm routes.

Surfaces the cached space-weather grid plus storm catalogue derived from the
v1 labels parquet.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from epb_detector.config import SETTINGS
from epb_detector.external import space_weather

router = APIRouter(prefix="/storms", tags=["storms"])


def _latest_labels_path() -> Path | None:
    """Return the most recent ``labels_v*.parquet`` (sorted lexicographically)."""
    candidates = sorted(SETTINGS.paths.data_processed.glob("labels_v*.parquet"))
    return candidates[-1] if candidates else None


@lru_cache(maxsize=1)
def _load_labels_cached(_mtime_key: tuple[str, float]) -> pd.DataFrame:
    """Cached parquet read keyed by (path, mtime). Auto-invalidates on rewrite."""
    path, _ = _mtime_key
    return pd.read_parquet(path)


def _load_labels() -> pd.DataFrame:
    path = _latest_labels_path()
    if path is None or not path.exists():
        return pd.DataFrame()
    return _load_labels_cached((str(path), path.stat().st_mtime))


@router.get("/timeline")
def timeline(
    t0: datetime | None = Query(default=None),
    t1: datetime | None = Query(default=None),
    step_hours: int = Query(default=1, ge=1, le=12),
) -> dict:
    """Hourly Kp + Dst + F10.7 grid for a UT range."""
    if t0 is None or t1 is None:
        kp_path = SETTINGS.paths.data_space_weather / "kp_ap_f107.parquet"
        if not kp_path.exists():
            return {"rows": []}
        df = pd.read_parquet(kp_path).sort_values("date")
        if df.empty:
            return {"rows": []}
        end = pd.Timestamp(df["date"].iloc[-1]).tz_convert("UTC")
        start = end - pd.Timedelta(days=60)
        t0 = start.to_pydatetime()
        t1 = end.to_pydatetime()
    if t0.tzinfo is None:
        t0 = t0.replace(tzinfo=timezone.utc)
    if t1.tzinfo is None:
        t1 = t1.replace(tzinfo=timezone.utc)
    grid = space_weather.build_space_weather_table(t0, t1)
    if grid.empty:
        return {"rows": []}
    grid = grid.iloc[::step_hours]
    return {
        "t0": t0.isoformat(),
        "t1": t1.isoformat(),
        "rows": [
            {
                "time": pd.Timestamp(r["time"]).isoformat(),
                "kp": None if pd.isna(r.get("kp")) else float(r["kp"]),
                "dst": None if pd.isna(r.get("dst")) else float(r["dst"]),
                "f107": None if pd.isna(r.get("F107obs")) else float(r["F107obs"]),
                "ap": None if pd.isna(r.get("ap")) else float(r["ap"]),
            }
            for r in grid.to_dict(orient="records")
        ],
    }


@lru_cache(maxsize=1)
def _catalog_payload(_mtime_key: tuple[str, float]) -> list[dict]:
    df = _load_labels()
    if df.empty or "storm_id" not in df.columns:
        return []
    grouped = (
        df[df["storm_id"] > 0]
        .groupby("storm_id")
        .agg(
            main_start=("window_start", "min"),
            recovery_end=("window_start", "max"),
            dst_min=("dst", "min"),
            dst_min_time=("dst", lambda s: df.loc[s.index[s.values.argmin()], "window_start"]),
            n_windows=("label", "size"),
            n_positive=("label", "sum"),
            stations=("sta", lambda s: ",".join(sorted(set(s)))),
            class_label=("storm_class", lambda s: s.value_counts().idxmin()),
        )
        .reset_index()
        .sort_values("dst_min")
    )
    return [
        {
            "storm_id": int(r.storm_id),
            "main_start": pd.Timestamp(r.main_start).isoformat(),
            "recovery_end": pd.Timestamp(r.recovery_end).isoformat(),
            "dst_min_time": pd.Timestamp(r.dst_min_time).isoformat(),
            "dst_min": float(r.dst_min) if pd.notna(r.dst_min) else None,
            "n_windows": int(r.n_windows),
            "n_positive": int(r.n_positive),
            "positive_rate": float(r.n_positive) / max(1, int(r.n_windows)),
            "stations": r.stations,
            "class_label": r.class_label,
        }
        for r in grouped.itertuples()
    ]


@router.get("/catalog")
def catalog() -> list[dict]:
    """Discrete storm events with their Dst min and phase boundaries.

    Result is cached per labels-parquet mtime; first call after ingest
    pays the groupby cost (~5 s on 1.7M rows), subsequent calls are
    served from memory.
    """
    path = _latest_labels_path()
    if path is None or not path.exists():
        return []
    return _catalog_payload((str(path), path.stat().st_mtime))


@router.get("/by-phase")
def by_phase() -> dict:
    """EPB-positive rate aggregated by storm phase."""
    df = _load_labels()
    if df.empty or "storm_phase" not in df.columns:
        return {"rows": []}
    grouped = (
        df.groupby("storm_phase")["label"]
        .agg(["count", "sum"])
        .rename(columns={"count": "n", "sum": "positives"})
        .reset_index()
    )
    grouped["rate"] = grouped["positives"] / grouped["n"]
    return {"rows": grouped.to_dict(orient="records")}


_ANALYSIS_PATH = SETTINGS.paths.data_processed / "analysis_v3.json"
_CATALOG_PATH = SETTINGS.paths.data_processed / "storm_catalog_v3.parquet"


@router.get("/v3/analysis")
def v3_analysis() -> dict:
    """Whole storms-v3 analysis JSON, served verbatim.

    Powers /findings and the upgraded /storms page. Returns 404-style
    empty structure when the file isn't on disk yet so the frontend can
    render a "not yet computed" state without crashing.
    """
    import json as _json
    if not _ANALYSIS_PATH.exists():
        return {"available": False}
    data = _json.loads(_ANALYSIS_PATH.read_text())
    data["available"] = True
    return data


@lru_cache(maxsize=1)
def _v3_catalog_records(_mtime_key: float) -> list[dict]:
    df = pd.read_parquet(_CATALOG_PATH)
    df = df.copy()
    for col in ("main_start", "dst_min_time", "recovery_end"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return df.sort_values("dst_min_time").to_dict(orient="records")


@router.get("/v3/catalog")
def v3_catalog(intense_only: bool = True) -> list[dict]:
    """Storm catalog with the v3 enrichments (lt_bin, season, ...)."""
    if not _CATALOG_PATH.exists():
        return []
    rows = _v3_catalog_records(_CATALOG_PATH.stat().st_mtime)
    if intense_only:
        rows = [r for r in rows if r.get("is_intense_or_stronger")]
    return rows


@router.get("/v3/figure/{name}")
def v3_figure(name: str):
    """Serve a PNG figure produced by paper/scripts/make_fig*.py.

    Convenience for the web pages that want to embed a static fig
    without copying assets into the Next.js public dir at deploy time.
    Only PNG with a curated allow-list to keep this from becoming a
    generic file server.
    """
    from fastapi.responses import FileResponse

    safe = {
        f"fig{n:02d}_{stem}"
        for n, stem in (
            (12, "storm_vs_quiet_v3"),
            (13, "storm_lt_polar"),
            (14, "intensity_curve"),
            (15, "solar_cycle_strip"),
            (16, "recovery_duration"),
            (17, "precursor"),
            (18, "cycle_modulation"),
            (19, "station_lag"),
        )
    }
    if name not in safe:
        raise HTTPException(404, "unknown figure")

    fig_path = SETTINGS.paths.repo_root / "paper" / "figures" / f"{name}.png"
    if not fig_path.exists():
        raise HTTPException(404, f"{name} not yet rendered")
    return FileResponse(fig_path, media_type="image/png")


@lru_cache(maxsize=4)
def _v3_solar_cycle_payload(
    _sw_mtime: float, _cat_mtime: float, start_iso: str, end_iso: str
) -> dict:
    """Cached SSN line + storm dots, monthly down-sampled to keep the
    payload small. The chart was already aggregating to monthly on the
    client; we now do it server-side so the wire payload drops by ~30×.
    """
    sw_path = SETTINGS.paths.data_space_weather / "kp_ap_f107.parquet"
    sw = pd.read_parquet(sw_path)
    sw["date"] = pd.to_datetime(sw["date"], utc=True)
    start = pd.Timestamp(start_iso)
    end = pd.Timestamp(end_iso)
    sw = sw[(sw["date"] >= start) & (sw["date"] <= end)]

    # Monthly mean SSN — 132 points for 11 years instead of 4498 daily rows.
    sw_month = (
        sw.dropna(subset=["SN"])
        .assign(_m=sw["date"].dt.to_period("M").dt.to_timestamp(tz="UTC"))
        .groupby("_m", as_index=False)["SN"]
        .mean()
        .rename(columns={"_m": "date"})
    )
    ssn_rows = [
        {"date": pd.Timestamp(r["date"]).isoformat(), "ssn": float(r["SN"])}
        for r in sw_month.to_dict(orient="records")
    ]

    storms_rows: list[dict] = []
    if _CATALOG_PATH.exists():
        cat = pd.read_parquet(_CATALOG_PATH)
        cat["dst_min_time"] = pd.to_datetime(cat["dst_min_time"], utc=True)
        cat = cat[(cat["dst_min_time"] >= start) & (cat["dst_min_time"] <= end)]
        for r in cat.to_dict(orient="records"):
            storms_rows.append(
                {
                    "storm_id": int(r["storm_id"]),
                    "dst_min_time": r["dst_min_time"].isoformat(),
                    "abs_dst_min": float(abs(r["dst_min_value"])),
                    "storm_class": r["storm_class"],
                    "is_intense_or_stronger": bool(r.get("is_intense_or_stronger", False)),
                }
            )
    return {"ssn": ssn_rows, "storms": storms_rows}


@router.get("/v3/solar-cycle")
def v3_solar_cycle(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
) -> dict:
    """Monthly SSN series + storm dots — feeds the /storms top strip.

    Result is cached per (sw-parquet mtime, catalog mtime, range).
    """
    sw_path = SETTINGS.paths.data_space_weather / "kp_ap_f107.parquet"
    if not sw_path.exists():
        return {"ssn": [], "storms": []}
    if start is None:
        start = pd.Timestamp("2014-01-01", tz="UTC").to_pydatetime()
    if end is None:
        end = pd.Timestamp.now(tz="UTC").to_pydatetime()
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    sw_mtime = sw_path.stat().st_mtime
    cat_mtime = _CATALOG_PATH.stat().st_mtime if _CATALOG_PATH.exists() else 0.0
    return _v3_solar_cycle_payload(
        sw_mtime, cat_mtime, start.isoformat(), end.isoformat()
    )


@router.get("/superposed-epoch")
def superposed_epoch() -> dict:
    """Per-hour EPB-positive rate vs hours from Dst min."""
    df = _load_labels()
    if df.empty or "hours_from_dst_min" not in df.columns:
        return {"rows": []}
    storm = df[df["storm_id"] > 0].copy()
    storm["bin"] = storm["hours_from_dst_min"].round().astype("Int64")
    grouped = (
        storm.groupby("bin")["label"]
        .agg(["count", "sum"])
        .rename(columns={"count": "n", "sum": "positives"})
        .reset_index()
    )
    grouped["rate"] = grouped["positives"] / grouped["n"].clip(lower=1)
    return {"rows": grouped.to_dict(orient="records")}
