"""Tests for feature extraction."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from epb_detector.features import pipeline, statistics, windows
from epb_detector.io import readers


def _synthetic_arc(n: int = 240, t0: str = "2023-12-22T22:00:00Z") -> pd.DataFrame:
    """A 60-minute synthetic arc at 15-second cadence."""
    times = pd.date_range(t0, periods=n, freq="15s", tz="UTC")
    return pd.DataFrame(
        {
            "time": times,
            "ROTI": np.linspace(0.05, 0.6, n),
            "Elevation": np.full(n, 45.0),
            "Longitude": np.full(n, 315.0),
            "Latitude": np.full(n, -3.0),
            "STA": "TEST",
            "SAT": "G01",
        }
    )


def test_split_arcs_detects_gap() -> None:
    df = _synthetic_arc(n=120)
    # Insert a 15-minute gap halfway through.
    df.loc[60:, "time"] = df.loc[60:, "time"] + pd.Timedelta(minutes=15)
    arcs = windows.split_arcs(df, gap_seconds=600.0)
    assert len(arcs) == 2
    assert len(arcs[0]) == 60
    assert len(arcs[1]) == 60


def test_make_windows_sliding() -> None:
    df = _synthetic_arc()
    wins = windows.make_windows(df, sta="TEST", sat="G01", window_minutes=10, stride_minutes=5)
    assert len(wins) >= 5
    for w in wins:
        assert (w.end - w.start) == pd.Timedelta(minutes=10)
        assert (w.samples["time"] >= w.start).all()


def test_duration_above_basic() -> None:
    times = pd.Series(pd.date_range("2024-01-01", periods=4, freq="60s", tz="UTC"))
    values = pd.Series([0.1, 0.6, 0.7, 0.2])
    # Two consecutive samples at threshold 0.5 → ~120s above.
    duration = statistics.duration_above(times, values, threshold=0.5)
    assert 110 <= duration <= 130


def test_slope_per_minute_linear() -> None:
    times = pd.Series(pd.date_range("2024-01-01", periods=10, freq="60s", tz="UTC"))
    values = pd.Series(np.arange(10, dtype=float))  # 1 unit / minute
    slope = statistics.slope_per_minute(times, values)
    assert slope == pytest.approx(1.0, abs=1e-6)


def test_build_features_on_real_roti(sample_roti_path: Path) -> None:
    roti = readers.read_roti(sample_roti_path)
    feats = pipeline.build_features(roti)
    assert not feats.empty
    expected_cols = {
        "sta",
        "sat",
        "window_start",
        "window_end",
        "roti_max",
        "roti_p95",
        "roti_duration_above",
        "elevation_mean",
        "qd_lat_mean",
        "local_time_mean",
        "n_samples",
    }
    assert expected_cols.issubset(feats.columns)
    assert (feats["sta"] == "SALU").all()
    assert feats["sat"].nunique() > 5  # multiple GPS satellites observed
    assert feats["roti_max"].notna().mean() > 0.95
    # Reasonable QD-lat for SALU (low latitude, ~5°S).
    assert feats["qd_lat_mean"].abs().mean() < 25
