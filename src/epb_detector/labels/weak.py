"""Weak labels for EPB detection.

Heuristic v1 (rule_version = ``weak-v1``). A 10-min window is labelled
positive when **all** of the following hold:

1. Local solar time at the IPP is between 19h and 06h (nighttime band — EPBs
   are an after-sunset Rayleigh–Taylor instability of the bottom-side F2
   layer, see Pi et al., 1997, GRL).
2. ROTI sustained ≥ 0.5 TECU/min for at least 5 minutes within the window.
   The 0.5 threshold is the classical detection level for irregularities
   (Pi et al., 1997). The sustained-duration criterion suppresses transient
   cycle-slip residuals that survive the screening stage.
3. At least 2 satellites trip rule (2) inside a ±10° IPP-longitude corridor
   centered on the candidate window — this is the multi-satellite criterion
   adopted by Cherniak, Krankowski & Zakharenkova (2014, Adv. Space Res.).
4. The IPP is at quasi-dipole latitude ``|QD-lat| ≤ 20°``, i.e. equatorial
   region — suppresses auroral irregularities.

All thresholds are configurable via :class:`epb_detector.config.LabelConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from epb_detector.config import SETTINGS


@dataclass(slots=True)
class LabelResult:
    labels: pd.DataFrame  # window features + label, source, rule_version
    rule_version: str


def _local_time_in_night_band(lt_hours: pd.Series, start: float, end: float) -> pd.Series:
    """True for samples whose local time falls in the [start, end] night band.

    The band wraps midnight (start > end means [start, 24) ∪ [0, end]).
    """
    lt = lt_hours.fillna(-1.0)
    if start <= end:
        return (lt >= start) & (lt <= end)
    return (lt >= start) | (lt <= end)


def label_features(features: pd.DataFrame) -> LabelResult:
    """Apply the weak-label heuristic to a window-level feature frame.

    The input frame is expected to come from
    :func:`epb_detector.features.pipeline.build_features`. It must contain at
    minimum: ``sta``, ``sat``, ``window_start``, ``window_end``, ``roti_max``,
    ``roti_duration_above`` (seconds), ``ipp_lon_mean``, ``qd_lat_mean``, and
    ``local_time_mean``.
    """
    cfg = SETTINGS.labels
    df = features.copy()

    night = _local_time_in_night_band(
        df["local_time_mean"], cfg.night_local_time_start, cfg.night_local_time_end
    )
    sustained = df["roti_duration_above"].fillna(0.0) >= cfg.sustained_minutes * 60.0
    above_thresh = df["roti_max"].fillna(-np.inf) >= cfg.roti_threshold_tecu_per_min
    equatorial = df["qd_lat_mean"].abs().fillna(np.inf) <= cfg.qd_lat_max_abs_deg

    # Single-satellite candidate.
    single_pos = (night & sustained & above_thresh & equatorial).fillna(False)

    # Multi-satellite criterion: count single_pos windows from *other* sats whose
    # window_start is within ±5 min of this one and whose IPP-longitude is
    # within ±lon_window_deg.
    multi_count = _count_concurrent_positives(
        df, single_pos, cfg.multi_sat_lon_window_deg, time_tolerance_minutes=5.0
    )
    multi_ok = multi_count >= cfg.multi_sat_min_count

    label = (single_pos & multi_ok).astype("int8")
    out = df.assign(
        label=label,
        label_source="weak",
        rule_version=cfg.rule_version,
        rule_single_pos=single_pos,
        rule_concurrent_sats=multi_count,
    )
    return LabelResult(labels=out, rule_version=cfg.rule_version)


def _count_concurrent_positives(
    df: pd.DataFrame,
    single_pos: pd.Series,
    lon_window_deg: float,
    time_tolerance_minutes: float,
) -> pd.Series:
    """For each row, count *other-satellite* single_pos rows nearby in (t, lon)."""
    if df.empty:
        return pd.Series([], dtype="int32", index=df.index)
    pos = df.loc[single_pos, ["sat", "window_start", "ipp_lon_mean"]].copy()
    if pos.empty:
        return pd.Series(np.zeros(len(df), dtype="int32"), index=df.index)
    pos = pos.sort_values("window_start").reset_index()
    # Use timezone-naive datetime64[ns] for vectorized arithmetic.
    pos_times = pd.DatetimeIndex(pos["window_start"]).tz_convert(None).to_numpy()
    pos_lons = pos["ipp_lon_mean"].to_numpy()
    pos_sats = pos["sat"].to_numpy()
    tol = np.timedelta64(int(time_tolerance_minutes * 60), "s")

    df_times = pd.DatetimeIndex(df["window_start"]).tz_convert(None).to_numpy()
    df_lons = df["ipp_lon_mean"].to_numpy()
    df_sats = df["sat"].to_numpy()

    # Count distinct satellites (including the candidate's own) whose positive
    # window is within ±tol minutes and ±lon_window_deg of the candidate.
    counts = np.zeros(len(df), dtype="int32")
    for i in range(len(df)):
        t = df_times[i]
        lon = df_lons[i]
        mask = (
            (np.abs(pos_times - t) <= tol)
            & (np.abs(_lon_diff(pos_lons, lon)) <= lon_window_deg)
        )
        counts[i] = int(np.unique(pos_sats[mask]).size)
    return pd.Series(counts, index=df.index)


def _lon_diff(a: np.ndarray, b: float) -> np.ndarray:
    """Shortest signed longitude difference, accounting for the 0/360 wrap."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return d
