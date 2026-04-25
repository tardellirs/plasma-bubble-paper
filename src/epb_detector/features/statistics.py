"""Window-level statistical features."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_p95(x: pd.Series) -> float:
    s = x.dropna()
    if s.empty:
        return float("nan")
    return float(np.percentile(s.to_numpy(), 95))


def _safe_max(x: pd.Series) -> float:
    s = x.dropna()
    return float("nan") if s.empty else float(s.max())


def _safe_mean(x: pd.Series) -> float:
    s = x.dropna()
    return float("nan") if s.empty else float(s.mean())


def _safe_std(x: pd.Series) -> float:
    s = x.dropna()
    if len(s) < 2:
        return float("nan")
    return float(s.std(ddof=1))


def duration_above(times: pd.Series, values: pd.Series, threshold: float) -> float:
    """Cumulative seconds where ``values >= threshold``.

    Sums the gap to the next sample for each above-threshold sample. Final
    sample is given the median sample period as its weight.
    """
    if values.empty:
        return 0.0
    times_dt = pd.to_datetime(times.to_numpy())
    deltas = np.diff(times_dt) / np.timedelta64(1, "s")
    if deltas.size:
        median_dt = float(np.median(deltas))
        weights = np.append(deltas, median_dt)
    else:
        weights = np.array([0.0])
    above = (values.fillna(-np.inf).to_numpy() >= threshold).astype(float)
    return float((above * weights).sum())


def slope_per_minute(times: pd.Series, values: pd.Series) -> float:
    """OLS slope of ``values`` against time, in units / minute."""
    s = values.dropna()
    if len(s) < 2:
        return float("nan")
    t_seconds = (times.loc[s.index] - times.loc[s.index].iloc[0]).dt.total_seconds().to_numpy()
    if not np.any(t_seconds):
        return float("nan")
    coeffs = np.polyfit(t_seconds / 60.0, s.to_numpy(), 1)
    return float(coeffs[0])


def roti_features(
    times: pd.Series, roti: pd.Series, *, threshold_tecu_per_min: float
) -> dict[str, float]:
    return {
        "roti_max": _safe_max(roti),
        "roti_p95": _safe_p95(roti),
        "roti_mean": _safe_mean(roti),
        "roti_std": _safe_std(roti),
        "roti_duration_above": duration_above(times, roti, threshold_tecu_per_min),
        "roti_slope": slope_per_minute(times, roti),
    }


def dtec_features(times: pd.Series, dtec: pd.Series) -> dict[str, float]:
    return {
        "dtec_max": _safe_max(dtec),
        "dtec_p95": _safe_p95(dtec),
        "dtec_std": _safe_std(dtec),
        "dtec_slope": slope_per_minute(times, dtec),
    }


def sidx_features(sidx: pd.Series) -> dict[str, float]:
    return {
        "sidx_max": _safe_max(sidx),
        "sidx_mean": _safe_mean(sidx),
    }
