"""Parsers for pyOASIS output text files.

All readers normalize:
- ``-999999.999`` (NaN sentinel used by pyOASIS) → ``numpy.nan``
- MJD (Modified Julian Date) → timezone-aware UTC ``pandas.Timestamp``
- Longitude → 0..360° (matches pyOASIS convention)

Returned DataFrames are sorted by (sat, time) when applicable.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

NAN_SENTINEL = -999999.999

# Modified Julian Date epoch (1858-11-17 00:00:00 UTC). pandas requires a
# tz-naive origin; we localize after the offset.
_MJD_EPOCH_NAIVE = pd.Timestamp("1858-11-17")


def mjd_to_utc(mjd: pd.Series | np.ndarray) -> pd.Series:
    """Convert Modified Julian Date (days) → tz-aware UTC ``Timestamp``."""
    arr = np.asarray(mjd, dtype="float64")
    seconds = arr * 86400.0
    naive = pd.to_datetime(seconds, unit="s", origin=_MJD_EPOCH_NAIVE)
    return naive.tz_localize("UTC")


def _replace_sentinel(df: pd.DataFrame, cols: list[str] | None = None) -> pd.DataFrame:
    cols = cols or [c for c in df.columns if df[c].dtype.kind == "f"]
    for col in cols:
        df[col] = df[col].where(df[col] != NAN_SENTINEL, np.nan)
    return df


def read_index_txt(path: Path | str, value_col: str) -> pd.DataFrame:
    """Read a generic ROTI/DTEC/SIDX-style file emitted by pyOASIS.

    Columns are tab-delimited. ``value_col`` is the metric name in the file
    header (``"ROTI"``, ``"DTEC"``, ``"SIDX"``).
    """
    df = pd.read_csv(path, sep="\t", engine="python")
    df.columns = [c.strip() for c in df.columns]
    df = _replace_sentinel(df)
    if "MJD" in df.columns:
        df["time"] = mjd_to_utc(df["MJD"])
    if value_col in df.columns:
        df[value_col] = df[value_col].astype("float64")
    sort_cols = [c for c in ("SAT", "time") if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols, kind="stable").reset_index(drop=True)
    return df


def read_roti(path: Path | str) -> pd.DataFrame:
    """ROTI series: ``MJD | Longitude | Latitude | Height | Elevation | ROTI | STA | SAT``."""
    return read_index_txt(path, "ROTI")


def read_dtec(path: Path | str) -> pd.DataFrame:
    """ΔTEC series: ``date | time | MJD | Longitude | Latitude | Height | Elevation | DTEC | STA | SAT``."""
    return read_index_txt(path, "DTEC")


def read_sidx(path: Path | str) -> pd.DataFrame:
    """SIDX series: ``MJD | Longitude | Latitude | Height | Elevation | SIDX | SIDX15 | STA | SAT``."""
    return read_index_txt(path, "SIDX")


def read_rnx3(path: Path | str) -> pd.DataFrame:
    """Per-satellite ``.RNX3`` (leveled geometry-free + IPP geometry).

    Has a ``mini_flag`` column ('Y' valid, 'N' filtered out by leveling).
    """
    df = pd.read_csv(path, sep="\t", engine="python", na_values=["None"])
    df.columns = [c.strip() for c in df.columns]
    df = _replace_sentinel(df)
    if "mjd" in df.columns:
        df["time"] = mjd_to_utc(df["mjd"])
    return df


def read_rnx3_merged(path: Path | str) -> pd.DataFrame:
    """Merged ``*_RNX3_merged.txt`` aggregating all satellites for a station-day."""
    df = pd.read_csv(path, sep="\t", engine="python", na_values=["None"])
    df.columns = [c.strip() for c in df.columns]
    df = _replace_sentinel(df)
    if "mjd" in df.columns:
        df["time"] = mjd_to_utc(df["mjd"])
    sort_cols = [c for c in ("satellite", "time") if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols, kind="stable").reset_index(drop=True)
    return df


# Column layout for *_L1L2.TEC (no header in file).
_TEC_COLS = [
    "domain",
    "MJD",
    "Longitude",
    "Latitude",
    "Height",
    "Elevation",
    "Lon_offset",
    "vTEC",
]


def read_tec(path: Path | str) -> pd.DataFrame:
    """Calibrated TEC file (``*_L1L2.TEC``). Whitespace-delimited, no header."""
    df = pd.read_csv(path, sep=r"\s+", engine="python", header=None, names=_TEC_COLS)
    df = _replace_sentinel(df)
    df["time"] = mjd_to_utc(df["MJD"])
    return df.sort_values("time").reset_index(drop=True)


def read_dcb(path: Path | str) -> pd.DataFrame:
    """Differential Code Bias file (``*_L1L2.DCB``).

    Columns: ``sat_index | dcb | status``. ``sat_index`` is the row counter
    used by pyOASIS's TEC solver (one row per arc segment); ``status`` is the
    arc index. Both are preserved as nullable integers.
    """
    df = pd.read_csv(
        path,
        sep=r"\s+",
        engine="python",
        header=None,
        names=["sat_index", "dcb", "status"],
        dtype={"sat_index": "Int64", "dcb": "float64", "status": "Int64"},
    )
    df = _replace_sentinel(df, cols=["dcb"])
    return df


__all__ = [
    "NAN_SENTINEL",
    "mjd_to_utc",
    "read_dcb",
    "read_dtec",
    "read_index_txt",
    "read_rnx3",
    "read_rnx3_merged",
    "read_roti",
    "read_sidx",
    "read_tec",
]
