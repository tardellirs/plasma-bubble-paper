"""Geomagnetic-storm routes.

Surfaces the cached space-weather grid plus storm catalogue derived from the
v1 labels parquet.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Query

from epb_detector.config import SETTINGS
from epb_detector.external import space_weather

router = APIRouter(prefix="/storms", tags=["storms"])


def _latest_labels_path() -> Path | None:
    """Return the most recent ``labels_v*.parquet`` (sorted lexicographically)."""
    candidates = sorted(SETTINGS.paths.data_processed.glob("labels_v*.parquet"))
    return candidates[-1] if candidates else None


def _load_labels() -> pd.DataFrame:
    path = _latest_labels_path()
    if path is None or not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


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


@router.get("/catalog")
def catalog() -> list[dict]:
    """Discrete storm events with their Dst min and phase boundaries."""
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
