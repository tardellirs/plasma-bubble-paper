"""Tests for storm classifier and external label sources."""

from __future__ import annotations

import numpy as np
import pandas as pd

from epb_detector.external import case_studies, storms
from epb_detector.labels import v2_external


def test_classify_storm_dst_bins() -> None:
    s = storms.classify_storm_dst(np.array([10.0, -29.0, -40.0, -75.0, -150.0, -300.0]))
    assert s.tolist() == ["quiet", "quiet", "moderate", "intense", "severe", "super"]


def test_detect_storms_simple_dip() -> None:
    times = pd.date_range("2024-05-10", periods=24, freq="h", tz="UTC")
    dst = pd.Series([10] * 8 + [-40, -80, -120, -150, -120, -80, -40, -10] + [10] * 8, dtype="float64")
    sw = pd.DataFrame({"time": times, "dst": dst})
    events = storms.detect_storms(sw)
    assert len(events) == 1
    assert events[0].storm_class in ("severe", "intense")
    assert events[0].dst_min_value == -150.0


def test_detect_storms_quiet_returns_empty() -> None:
    times = pd.date_range("2024-01-01", periods=12, freq="h", tz="UTC")
    sw = pd.DataFrame({"time": times, "dst": np.linspace(-10, 5, 12)})
    assert storms.detect_storms(sw) == []


def test_annotate_phase_main_then_recovery() -> None:
    times = pd.date_range("2024-05-10", periods=24, freq="h", tz="UTC")
    dst = pd.Series([10] * 4 + [-40, -80, -120, -150, -120, -80, -40, -10] + [10] * 12, dtype="float64")
    sw = pd.DataFrame({"time": times, "dst": dst})
    events = storms.detect_storms(sw)
    annotated = storms.annotate_storm_phase(sw, events)
    assert (annotated["storm_phase"] == "main").any()
    assert (annotated["storm_phase"] == "recovery").any()
    assert (annotated["storm_phase"] == "none").any()
    assert annotated.loc[
        annotated["dst"] == -150.0, "hours_from_dst_min"
    ].iloc[0] == 0.0


def test_attach_to_features_aligns_in_time() -> None:
    sw = pd.DataFrame(
        {
            "time": pd.date_range("2023-12-22", periods=4, freq="h", tz="UTC"),
            "dst": [-10.0, -40.0, -90.0, -50.0],
            "kp": [1.0, 4.0, 7.0, 5.0],
        }
    )
    feats = pd.DataFrame(
        {
            "sta": ["SALU", "SALU"],
            "sat": ["G01", "G01"],
            "window_start": pd.to_datetime(
                ["2023-12-22 01:30:00", "2023-12-22 02:30:00"], utc=True
            ),
        }
    )
    out = storms.attach_to_features(feats, sw)
    assert (out["dst"].iloc[0] == -40.0) and (out["dst"].iloc[1] == -90.0)


def test_case_studies_loaded() -> None:
    cases = case_studies.load_cases()
    assert len(cases) >= 5
    salu_2015 = case_studies.cases_for("SALU", 2015, 359)
    assert len(salu_2015) == 1
    assert "Picanço" in salu_2015[0].reference


def test_v2_label_combines_sources() -> None:
    df = pd.DataFrame(
        {
            "sta": ["SALU", "SALU"],
            "sat": ["G01", "G02"],
            "year": [2015, 2015],
            "doy": [359, 359],
            "window_start": pd.to_datetime(
                ["2015-12-25 22:00:00", "2015-12-25 22:01:00"], utc=True
            ),
            "window_end": pd.to_datetime(
                ["2015-12-25 22:10:00", "2015-12-25 22:11:00"], utc=True
            ),
            "roti_max": [1.2, 0.9],
            "roti_duration_above": [600, 420],
            "ipp_lon_mean": [315.0, 316.0],
            "qd_lat_mean": [-2.0, -3.0],
            "local_time_mean": [22.0, 22.1],
        }
    )
    out = v2_external.label_features_v2(df)
    # Both rows match a literature case AND the weak rule → confidence 1.0.
    assert (out["label"] == 1).all()
    assert (out["label_confidence"] == 1.0).all()
    assert (out["label_source"] == "weak+literature").all()
    assert (out["rule_version"] == "v2").all()


def test_v2_label_literature_only_at_daytime_does_not_fire() -> None:
    # Same date as a literature case but during local daytime → literature
    # label should NOT light up because we gate it to the night band.
    df = pd.DataFrame(
        {
            "sta": ["SALU"],
            "sat": ["G01"],
            "year": [2015],
            "doy": [359],
            "window_start": pd.to_datetime(["2015-12-25 14:00:00"], utc=True),
            "window_end": pd.to_datetime(["2015-12-25 14:10:00"], utc=True),
            "roti_max": [0.1],
            "roti_duration_above": [0],
            "ipp_lon_mean": [315.0],
            "qd_lat_mean": [-2.0],
            "local_time_mean": [14.0],
        }
    )
    out = v2_external.label_features_v2(df)
    assert (out["label"] == 0).all()
    assert (out["label_literature"] == 0).all()
