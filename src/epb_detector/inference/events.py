"""Convert window-level probabilities into discrete bubble events."""

from __future__ import annotations

import pandas as pd


def windows_to_events(df: pd.DataFrame, *, min_prob: float = 0.5, gap_tolerance_minutes: float = 5.0) -> pd.DataFrame:
    """Merge consecutive positive windows per (sta, sat) into events.

    Two consecutive windows on the same satellite belong to the same event when
    their start/end fall within ``gap_tolerance_minutes`` of each other.
    """
    if df.empty or "epb_probability" not in df.columns:
        return pd.DataFrame()

    pos = df[df["epb_probability"] >= min_prob].copy()
    if pos.empty:
        return pd.DataFrame()

    pos = pos.sort_values(["sta", "sat", "window_start"]).reset_index(drop=True)
    tol = pd.Timedelta(minutes=gap_tolerance_minutes)
    new_event = (
        (pos["sta"] != pos["sta"].shift())
        | (pos["sat"] != pos["sat"].shift())
        | (pos["window_start"] - pos["window_end"].shift() > tol)
    )
    pos["event_id"] = new_event.cumsum()

    grouped = pos.groupby("event_id", sort=False).agg(
        sta=("sta", "first"),
        sat=("sat", "first"),
        start=("window_start", "min"),
        end=("window_end", "max"),
        n_windows=("epb_probability", "size"),
        peak_probability=("epb_probability", "max"),
        peak_roti=("roti_max", "max"),
        ipp_lon_mean=("ipp_lon_mean", "mean"),
        ipp_lat_mean=("ipp_lat_mean", "mean"),
        qd_lat_mean=("qd_lat_mean", "mean"),
    )
    grouped["duration_minutes"] = (
        (grouped["end"] - grouped["start"]).dt.total_seconds() / 60.0
    )
    return grouped.reset_index(drop=True)
