"""Geometric features computed at the IPP."""

from __future__ import annotations

import warnings
from datetime import timezone

import numpy as np
import pandas as pd

from epb_detector.geo import coords, magnetic


def _ts_to_naive_utc_datetime(ts: pd.Timestamp) -> "pd.Timestamp":
    if ts.tzinfo is not None:
        ts = ts.tz_convert(timezone.utc).tz_localize(None)
    # Drop sub-second precision to keep aacgmv2 (which expects datetime, not
    # Timestamp) happy without warnings about nonzero nanoseconds.
    return ts.floor("s").to_pydatetime()


def _nanmean_quiet(arr: np.ndarray) -> float:
    if arr.size == 0:
        return float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        value = float(np.nanmean(arr))
    return value


def geometric_features(
    times: pd.Series,
    longitude_deg: pd.Series,
    latitude_deg: pd.Series,
    elevation_deg: pd.Series,
) -> dict[str, float]:
    """Window-aggregated IPP geometry features.

    ``longitude_deg`` is expected in pyOASIS's 0–360° convention; we wrap to
    ±180 for the QD-lat lookup but report the mean in 0–360 to stay consistent
    with the source data.
    """
    if times.empty:
        return {
            "elevation_mean": float("nan"),
            "ipp_lon_mean": float("nan"),
            "ipp_lat_mean": float("nan"),
            "qd_lat_mean": float("nan"),
            "local_time_mean": float("nan"),
            "n_samples": 0,
        }
    lon_180 = ((longitude_deg + 180) % 360) - 180
    epoch = _ts_to_naive_utc_datetime(pd.Timestamp(times.iloc[0]))
    qd_lat, _ = magnetic.qd_lat_lon(
        latitude_deg.to_numpy(),
        lon_180.to_numpy(),
        # IPP coordinates are at the ionospheric shell; aacgmv2 needs h_km > 0.
        np.full(len(times), coords.SHELL_HEIGHT_KM),
        epoch,
    )
    times_utc_naive = pd.DatetimeIndex(times).tz_convert(None).to_numpy()
    lt = coords.utc_to_local_time_hours(times_utc_naive, lon_180)
    return {
        "elevation_mean": float(elevation_deg.mean()),
        "ipp_lon_mean": float(longitude_deg.mean()),
        "ipp_lat_mean": float(latitude_deg.mean()),
        "qd_lat_mean": _nanmean_quiet(np.asarray(qd_lat)),
        "local_time_mean": _nanmean_quiet(np.asarray(lt)),
        "n_samples": int(len(times)),
    }
