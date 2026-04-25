"""Tests for io.readers, validated against the SALU 2015-12-25 outputs in this repo."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from epb_detector.io import readers
from epb_detector.io.readers import NAN_SENTINEL, mjd_to_utc


def test_mjd_to_utc_known_epoch() -> None:
    # MJD 57381 == 2015-12-25 00:00:00 UTC
    ts = mjd_to_utc(np.array([57381.0]))
    assert ts[0] == pd.Timestamp("2015-12-25", tz="UTC")


def test_read_roti_schema_and_no_sentinel(sample_roti_path: Path) -> None:
    df = readers.read_roti(sample_roti_path)
    expected = {"MJD", "Longitude", "Latitude", "Height", "Elevation", "ROTI", "STA", "SAT", "time"}
    assert expected.issubset(df.columns)
    assert len(df) > 0
    assert df["STA"].iloc[0] == "SALU"
    assert df["SAT"].str.startswith("G").all()
    assert (df["Elevation"] >= 30).all(), "ROTI is filtered to El >= 30°"
    # No -999999.999 sentinels leaked through.
    for col in ("ROTI", "Longitude", "Latitude", "Elevation"):
        assert not (df[col] == NAN_SENTINEL).any()
    assert df["time"].dt.tz is not None
    assert df["time"].dt.date.iloc[0] == pd.Timestamp("2015-12-25").date()


def test_read_dtec_has_dtec_column(sample_dtec_path: Path) -> None:
    df = readers.read_dtec(sample_dtec_path)
    assert "DTEC" in df.columns
    assert "time" in df.columns
    assert df["DTEC"].notna().any()


def test_read_sidx_has_sidx_columns(sample_sidx_path: Path) -> None:
    df = readers.read_sidx(sample_sidx_path)
    assert {"SIDX", "SIDX15"}.issubset(df.columns)
    # SIDX is in mTECU/sec → ought to be small but positive on average for nighttime.
    assert (df["SIDX"].dropna() >= 0).mean() > 0.95


def test_read_rnx3_per_satellite(sample_rnx3_path: Path) -> None:
    df = readers.read_rnx3(sample_rnx3_path)
    assert {"satellite", "sta", "El", "Lon", "Lat", "mini_flag", "time"}.issubset(df.columns)
    assert df["satellite"].nunique() == 1  # per-sat file
    assert df["sta"].iloc[0] == "SALU"
    # mini_flag is 'Y' for valid; sentinel rows should already be NaN in LGF_combination.
    assert df["mini_flag"].isin(["Y", "N"]).all()


def test_read_rnx3_merged(sample_rnx3_merged_path: Path) -> None:
    df = readers.read_rnx3_merged(sample_rnx3_merged_path)
    assert df["satellite"].nunique() > 1
    assert df["sta"].nunique() == 1
    # Sentinels in LGF should have been replaced with NaN.
    assert not (df["LGF_combination"] == NAN_SENTINEL).any()


def test_read_tec_no_header(sample_tec_path: Path) -> None:
    df = readers.read_tec(sample_tec_path)
    assert {"MJD", "vTEC", "Elevation", "time"}.issubset(df.columns)
    # vTEC should be finite for the bulk of rows.
    assert df["vTEC"].notna().mean() > 0.9


def test_read_dcb(sample_dcb_path: Path) -> None:
    df = readers.read_dcb(sample_dcb_path)
    assert list(df.columns) == ["sat_index", "dcb", "status"]
    assert df["sat_index"].notna().all()
    assert (df["status"] >= 0).all()
    assert df["dcb"].notna().any()


@pytest.mark.parametrize(
    "fn",
    [readers.read_roti, readers.read_dtec, readers.read_sidx],
)
def test_index_files_sorted_by_sat_time(
    fn, sample_roti_path: Path, sample_dtec_path: Path, sample_sidx_path: Path
) -> None:
    paths = {
        readers.read_roti: sample_roti_path,
        readers.read_dtec: sample_dtec_path,
        readers.read_sidx: sample_sidx_path,
    }
    df = fn(paths[fn])
    # Stable ordering simplifies window construction downstream.
    for sat, g in df.groupby("SAT"):
        assert g["time"].is_monotonic_increasing, f"{sat} not monotonic"
