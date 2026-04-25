"""Storm-time classification and per-window space-weather context.

Storm class follows the Loewe & Prölss (1997) Dst convention used widely in
the EPB literature:

    quiet     : Dst > -30 nT
    moderate  : -50 < Dst ≤ -30 nT
    intense   : -100 < Dst ≤ -50 nT
    severe    : -250 < Dst ≤ -100 nT
    super     : Dst ≤ -250 nT

A *storm* is a contiguous period whose hourly minimum Dst reaches at least
moderate. We mark the **main phase** as the time from the first sub-zero
crossing before the minimum back through the minimum, and the **recovery
phase** as the time from the minimum until Dst returns above -30 nT.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

STORM_BIN_EDGES = np.array([-1e9, -250.0, -100.0, -50.0, -30.0, 1e9])
STORM_BIN_LABELS = ["super", "severe", "intense", "moderate", "quiet"]


def classify_storm_dst(dst_nt: pd.Series | np.ndarray) -> pd.Series:
    """Vectorised Dst → storm class label."""
    arr = np.asarray(dst_nt, dtype="float64")
    out = np.full(arr.shape, "unknown", dtype=object)
    finite = np.isfinite(arr)
    if finite.any():
        bins = np.digitize(arr[finite], STORM_BIN_EDGES[1:-1])
        out[finite] = np.array(STORM_BIN_LABELS)[bins]
    return pd.Series(out)


@dataclass(frozen=True, slots=True)
class StormEvent:
    storm_id: int
    main_start: pd.Timestamp
    dst_min_time: pd.Timestamp
    dst_min_value: float
    recovery_end: pd.Timestamp
    storm_class: str

    def to_dict(self) -> dict[str, object]:
        return {
            "storm_id": self.storm_id,
            "main_start": self.main_start.isoformat(),
            "dst_min_time": self.dst_min_time.isoformat(),
            "dst_min_value": float(self.dst_min_value),
            "recovery_end": self.recovery_end.isoformat(),
            "storm_class": self.storm_class,
        }


def detect_storms(
    sw: pd.DataFrame,
    *,
    threshold_nt: float = -30.0,
    min_dip_nt: float = -50.0,
) -> list[StormEvent]:
    """Detect contiguous storm episodes in an hourly Dst series.

    A run of rows with ``dst <= threshold_nt`` becomes one event when its
    minimum is at least ``min_dip_nt`` (i.e. moderate or stronger). Adjacent
    events separated by < 6 h above ``threshold_nt`` are merged.
    """
    if "dst" not in sw.columns or sw["dst"].isna().all():
        return []
    df = sw[["time", "dst"]].dropna().sort_values("time").reset_index(drop=True)
    if df.empty:
        return []

    in_storm = (df["dst"] <= threshold_nt).to_numpy()
    runs = _runs_of_true(in_storm)
    # Merge runs separated by short gaps.
    merged: list[tuple[int, int]] = []
    for start, end in runs:
        if merged and start - merged[-1][1] < 6:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))

    events: list[StormEvent] = []
    storm_id = 0
    for start, end in merged:
        chunk = df.iloc[start:end]
        if chunk.empty:
            continue
        min_idx = int(chunk["dst"].idxmin())
        dst_min = float(chunk.loc[min_idx, "dst"])
        if dst_min > min_dip_nt:
            continue
        storm_id += 1
        events.append(
            StormEvent(
                storm_id=storm_id,
                main_start=chunk["time"].iloc[0],
                dst_min_time=df.loc[min_idx, "time"],
                dst_min_value=dst_min,
                recovery_end=chunk["time"].iloc[-1],
                storm_class=str(classify_storm_dst(np.array([dst_min])).iloc[0]),
            )
        )
    return events


def _runs_of_true(mask: np.ndarray) -> list[tuple[int, int]]:
    if mask.size == 0:
        return []
    diff = np.diff(mask.astype(int))
    starts = list(np.where(diff == 1)[0] + 1)
    ends = list(np.where(diff == -1)[0] + 1)
    if mask[0]:
        starts.insert(0, 0)
    if mask[-1]:
        ends.append(len(mask))
    return list(zip(starts, ends, strict=True))


def annotate_storm_phase(sw: pd.DataFrame, events: list[StormEvent]) -> pd.DataFrame:
    """Append ``storm_phase`` and ``hours_from_dst_min`` columns to ``sw``.

    ``storm_phase`` is one of ``main``, ``recovery``, or ``none``.
    ``hours_from_dst_min`` is signed (negative before the minimum, positive
    after).
    """
    out = sw.copy().sort_values("time").reset_index(drop=True)
    out["storm_phase"] = "none"
    out["hours_from_dst_min"] = np.nan
    out["storm_id"] = 0
    if not events:
        return out

    times_idx = pd.DatetimeIndex(out["time"])
    if times_idx.tz is None:
        times_idx = times_idx.tz_localize("UTC")
    for ev in events:
        main_mask = (times_idx >= ev.main_start) & (times_idx <= ev.dst_min_time)
        rec_mask = (times_idx > ev.dst_min_time) & (times_idx <= ev.recovery_end)
        out.loc[main_mask, "storm_phase"] = "main"
        out.loc[rec_mask, "storm_phase"] = "recovery"
        union = main_mask | rec_mask
        if union.any():
            delta = (times_idx[union] - ev.dst_min_time).total_seconds() / 3600.0
            out.loc[union, "hours_from_dst_min"] = delta
            out.loc[union, "storm_id"] = ev.storm_id
    out["storm_class"] = classify_storm_dst(out["dst"]).to_numpy()
    return out


def attach_to_features(
    features: pd.DataFrame, sw: pd.DataFrame
) -> pd.DataFrame:
    """Merge per-window features with hourly space-weather context.

    Uses an as-of join on the hourly grid; each window inherits the most
    recent space-weather row (≤ 1 hour earlier).
    """
    if features.empty or sw.empty:
        return features
    feat = features.sort_values("window_start").reset_index(drop=True).copy()
    sw_sorted = sw.sort_values("time").reset_index(drop=True).copy()
    # Coerce both timestamp columns to nanosecond precision so merge_asof
    # accepts them — pandas refuses to mix datetime64[us] and datetime64[ns].
    feat["window_start"] = pd.to_datetime(feat["window_start"], utc=True).astype(
        "datetime64[ns, UTC]"
    )
    sw_sorted["time"] = pd.to_datetime(sw_sorted["time"], utc=True).astype(
        "datetime64[ns, UTC]"
    )
    return pd.merge_asof(
        feat,
        sw_sorted,
        left_on="window_start",
        right_on="time",
        direction="backward",
        tolerance=pd.Timedelta("3h"),
    ).drop(columns=["time"], errors="ignore")
