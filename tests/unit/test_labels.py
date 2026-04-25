"""Tests for weak-label heuristic."""

from __future__ import annotations

import pandas as pd

from epb_detector.labels import weak


def _row(sat: str, t: str, lon: float, *, roti_max: float, dur: float, qd_lat: float, lt: float) -> dict:
    return {
        "sta": "TEST",
        "sat": sat,
        "window_start": pd.Timestamp(t, tz="UTC"),
        "window_end": pd.Timestamp(t, tz="UTC") + pd.Timedelta(minutes=10),
        "roti_max": roti_max,
        "roti_duration_above": dur,
        "ipp_lon_mean": lon,
        "qd_lat_mean": qd_lat,
        "local_time_mean": lt,
    }


def test_single_window_alone_is_negative() -> None:
    df = pd.DataFrame(
        [_row("G01", "2023-12-22T22:00:00Z", 315.0, roti_max=1.2, dur=600, qd_lat=-2.0, lt=22.0)]
    )
    out = weak.label_features(df).labels
    assert out["rule_single_pos"].iloc[0]
    # No companion satellite → multi-sat criterion not met.
    assert out["label"].iloc[0] == 0


def test_two_satellites_concurrent_is_positive() -> None:
    rows = [
        _row("G01", "2023-12-22T22:00:00Z", 315.0, roti_max=1.2, dur=600, qd_lat=-2.0, lt=22.0),
        _row("G02", "2023-12-22T22:01:00Z", 316.0, roti_max=0.9, dur=420, qd_lat=-3.0, lt=22.1),
    ]
    out = weak.label_features(pd.DataFrame(rows)).labels
    assert (out["label"] == 1).all()


def test_daytime_event_is_negative() -> None:
    rows = [
        _row("G01", "2023-12-22T14:00:00Z", 315.0, roti_max=1.2, dur=600, qd_lat=-2.0, lt=14.0),
        _row("G02", "2023-12-22T14:01:00Z", 316.0, roti_max=0.9, dur=420, qd_lat=-3.0, lt=14.1),
    ]
    out = weak.label_features(pd.DataFrame(rows)).labels
    assert (out["label"] == 0).all()


def test_high_qd_lat_is_negative() -> None:
    # Auroral candidate — should be filtered by |QD-lat| ≤ 20°.
    rows = [
        _row("G01", "2023-12-22T22:00:00Z", 315.0, roti_max=1.2, dur=600, qd_lat=-65.0, lt=22.0),
        _row("G02", "2023-12-22T22:01:00Z", 316.0, roti_max=0.9, dur=420, qd_lat=-65.5, lt=22.1),
    ]
    out = weak.label_features(pd.DataFrame(rows)).labels
    assert (out["label"] == 0).all()


def test_short_burst_is_negative() -> None:
    # Sustained for only 60s, well below the 5-min requirement.
    rows = [
        _row("G01", "2023-12-22T22:00:00Z", 315.0, roti_max=1.2, dur=60, qd_lat=-2.0, lt=22.0),
        _row("G02", "2023-12-22T22:01:00Z", 316.0, roti_max=0.9, dur=60, qd_lat=-3.0, lt=22.1),
    ]
    out = weak.label_features(pd.DataFrame(rows)).labels
    assert (out["label"] == 0).all()


def test_far_apart_satellites_not_concurrent() -> None:
    # Same time, but lon difference > 10° → multi-sat criterion fails.
    rows = [
        _row("G01", "2023-12-22T22:00:00Z", 315.0, roti_max=1.2, dur=600, qd_lat=-2.0, lt=22.0),
        _row("G02", "2023-12-22T22:00:00Z", 340.0, roti_max=1.0, dur=600, qd_lat=-2.0, lt=23.7),
    ]
    out = weak.label_features(pd.DataFrame(rows)).labels
    assert (out["label"] == 0).all()


def test_lon_wrap_handled() -> None:
    # G01 at 1° E, G02 at 359° → 2° apart through the wrap.
    rows = [
        _row("G01", "2023-12-22T22:00:00Z", 1.0, roti_max=1.2, dur=600, qd_lat=-2.0, lt=22.0),
        _row("G02", "2023-12-22T22:00:00Z", 359.0, roti_max=0.9, dur=420, qd_lat=-3.0, lt=22.0),
    ]
    out = weak.label_features(pd.DataFrame(rows)).labels
    assert (out["label"] == 1).all()


def test_label_metadata_set() -> None:
    rows = [
        _row("G01", "2023-12-22T22:00:00Z", 315.0, roti_max=1.2, dur=600, qd_lat=-2.0, lt=22.0),
        _row("G02", "2023-12-22T22:01:00Z", 316.0, roti_max=0.9, dur=420, qd_lat=-3.0, lt=22.1),
    ]
    out = weak.label_features(pd.DataFrame(rows)).labels
    assert (out["label_source"] == "weak").all()
    assert (out["rule_version"] == "weak-v1").all()
    # Both sats themselves count → concurrent_sats == 2.
    assert (out["rule_concurrent_sats"].astype(int) == 2).all()
