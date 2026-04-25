"""Space-weather indices fetcher (Kp / ap / F10.7 / Dst).

All sources are public, no authentication needed:

- **Kp / ap / F10.7** — GFZ Potsdam, single ASCII file with 8 Kp values per UT
  day, 8 ap values, daily Ap, sunspot number, F10.7 obs and adjusted.
  ``https://kp.gfz.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt``

- **Dst** — World Data Centre Kyoto. Hourly values, organised in fixed-format
  HTML tables under ``/dst_provisional/<YYYYMM>/index.html`` (recent) or
  ``/dst_final/<YYYYMM>/index.html`` (definitive, lag of months).

Each fetcher caches its parsed output to ``data/space_weather/<index>.parquet``
and refuses to refetch within a TTL.
"""

from __future__ import annotations

import logging
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from epb_detector.config import SETTINGS

logger = logging.getLogger(__name__)

USER_AGENT = "epb-detector/0.1 (https://github.com/giorgiopicanco/OASIS)"

GFZ_KP_URL = "https://kp.gfz.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt"
WDC_DST_PROVISIONAL_URL = (
    "https://wdc.kugi.kyoto-u.ac.jp/dst_provisional/{yyyymm}/index.html"
)
WDC_DST_FINAL_URL = "https://wdc.kugi.kyoto-u.ac.jp/dst_final/{yyyymm}/index.html"


@dataclass(slots=True)
class FetchResult:
    df: pd.DataFrame
    cached: bool
    path: Path


def _request(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------------------------------------------------------------------------
# Kp / ap / F10.7
# ---------------------------------------------------------------------------

KP_COLUMNS = ["Kp1", "Kp2", "Kp3", "Kp4", "Kp5", "Kp6", "Kp7", "Kp8", "ap1", "ap2", "ap3", "ap4", "ap5", "ap6", "ap7", "ap8", "Ap", "SN", "F107obs", "F107adj"]


def fetch_kp_ap(force: bool = False, ttl_hours: float = 24.0) -> FetchResult:
    """Fetch the GFZ master Kp/ap/F10.7 file and cache it as parquet."""
    out = SETTINGS.paths.data_space_weather / "kp_ap_f107.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not force:
        age = datetime.now(timezone.utc).timestamp() - out.stat().st_mtime
        if age < ttl_hours * 3600:
            return FetchResult(pd.read_parquet(out), cached=True, path=out)
    logger.info("downloading %s", GFZ_KP_URL)
    raw = _request(GFZ_KP_URL).decode("utf-8", errors="replace")
    df = _parse_kp_text(raw)
    df.to_parquet(out, index=False)
    return FetchResult(df, cached=False, path=out)


def _parse_kp_text(raw: str) -> pd.DataFrame:
    rows: list[list[float]] = []
    for line in raw.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 27:
            continue
        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            continue
        # parts[3..6] are bookkeeping (days, days_m, BSR, dB)
        kp = [float(x) for x in parts[7:15]]
        ap = [float(x) for x in parts[15:23]]
        Ap = float(parts[23])
        SN = float(parts[24])
        f107obs = float(parts[25])
        f107adj = float(parts[26])
        rows.append([year, month, day, *kp, *ap, Ap, SN, f107obs, f107adj])
    df = pd.DataFrame(
        rows,
        columns=["year", "month", "day", *KP_COLUMNS],
    )
    df["date"] = pd.to_datetime(df[["year", "month", "day"]]).dt.tz_localize("UTC")
    return df


def kp_to_3hourly(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape the daily Kp/ap frame to a long 3-hourly time series."""
    long = df.melt(
        id_vars=["date"],
        value_vars=[f"Kp{i}" for i in range(1, 9)],
        var_name="slot",
        value_name="kp",
    )
    long["slot_idx"] = long["slot"].str[2:].astype(int)
    long["time"] = long["date"] + pd.to_timedelta((long["slot_idx"] - 1) * 3, unit="h")
    long = long[["time", "kp"]].sort_values("time").reset_index(drop=True)
    # Add ap aligned to the same 3-hour slots.
    ap_long = df.melt(
        id_vars=["date"],
        value_vars=[f"ap{i}" for i in range(1, 9)],
        var_name="slot",
        value_name="ap",
    )
    ap_long["slot_idx"] = ap_long["slot"].str[2:].astype(int)
    ap_long["time"] = ap_long["date"] + pd.to_timedelta(
        (ap_long["slot_idx"] - 1) * 3, unit="h"
    )
    return long.merge(ap_long[["time", "ap"]], on="time", how="left")


def f107_daily(df: pd.DataFrame) -> pd.DataFrame:
    return df[["date", "F107obs", "F107adj", "Ap", "SN"]].rename(columns={"date": "time"})


# ---------------------------------------------------------------------------
# Dst (WDC Kyoto)
# ---------------------------------------------------------------------------


def _yyyymm_range(start: datetime, end: datetime) -> list[str]:
    out: list[str] = []
    cursor = datetime(start.year, start.month, 1, tzinfo=timezone.utc)
    end_anchor = datetime(end.year, end.month, 1, tzinfo=timezone.utc)
    while cursor <= end_anchor:
        out.append(cursor.strftime("%Y%m"))
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)
    return out


def fetch_dst(start: datetime, end: datetime, force: bool = False) -> FetchResult:
    """Fetch hourly Dst between two dates from WDC Kyoto, parsing per month."""
    out = SETTINGS.paths.data_space_weather / "dst.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    existing = pd.read_parquet(out) if out.exists() and not force else pd.DataFrame()

    months_needed = _yyyymm_range(start, end)
    months_have = (
        set(existing["time"].dt.strftime("%Y%m").unique())
        if not existing.empty
        else set()
    )
    missing = [m for m in months_needed if m not in months_have]

    pieces: list[pd.DataFrame] = [existing] if not existing.empty else []
    for yyyymm in missing:
        for tmpl in (WDC_DST_FINAL_URL, WDC_DST_PROVISIONAL_URL):
            url = tmpl.format(yyyymm=yyyymm)
            try:
                raw = _request(url, timeout=30).decode("ascii", errors="replace")
            except Exception as e:
                logger.warning("Dst %s missing at %s (%s)", yyyymm, url, e)
                continue
            month_df = _parse_dst_html(raw, int(yyyymm[:4]), int(yyyymm[4:]))
            if not month_df.empty:
                pieces.append(month_df)
                break
    if not pieces:
        empty = pd.DataFrame(columns=["time", "dst"])
        empty.to_parquet(out, index=False)
        return FetchResult(empty, cached=False, path=out)

    merged = (
        pd.concat(pieces, ignore_index=True)
        .drop_duplicates(subset=["time"])
        .sort_values("time")
        .reset_index(drop=True)
    )
    merged.to_parquet(out, index=False)
    return FetchResult(merged, cached=False, path=out)


_DAY_LINE = re.compile(r"^\s*(\d{1,2})\s+(.+)$")


def _parse_dst_html(html: str, year: int, month: int) -> pd.DataFrame:
    """Extract the hourly Dst table from a WDC Kyoto monthly HTML page."""
    # The numbers we want are inside a <pre> block. Strip tags first.
    text = re.sub(r"<[^>]+>", "", html)
    rows: list[tuple[pd.Timestamp, float]] = []
    in_table = False
    for line in text.splitlines():
        if "DAY" in line and not in_table:
            in_table = True
            continue
        if not in_table:
            continue
        m = _DAY_LINE.match(line.rstrip())
        if not m:
            continue
        day = int(m.group(1))
        if day < 1 or day > 31:
            continue
        # The remaining tokens are 24 ints (Dst per UT hour). Some are negative
        # and run together: parse with a fixed-width strategy by re-extracting
        # all signed integer tokens from the rest of the line.
        rest = m.group(2)
        toks = re.findall(r"-?\d+", rest)
        if len(toks) < 24:
            continue
        for hour in range(24):
            try:
                ts = pd.Timestamp(year=year, month=month, day=day, hour=hour, tz="UTC")
            except (ValueError, OverflowError):
                continue
            try:
                rows.append((ts, float(toks[hour])))
            except ValueError:
                continue
    if not rows:
        return pd.DataFrame(columns=["time", "dst"])
    df = pd.DataFrame(rows, columns=["time", "dst"])
    return df.sort_values("time").reset_index(drop=True)


# ---------------------------------------------------------------------------
# High-level join
# ---------------------------------------------------------------------------


def build_space_weather_table(
    start: datetime, end: datetime, force: bool = False
) -> pd.DataFrame:
    """Return one table with a 1-hour grid covering [start, end] UTC.

    Columns: ``time, dst, kp, ap, F107obs, F107adj``. Non-Dst indices are
    forward-filled to the hourly grid.
    """
    kp_res = fetch_kp_ap(force=force)
    dst_res = fetch_dst(start, end, force=force)

    # Snap to whole UT hours so the grid aligns with the hourly Dst series.
    start_h = pd.Timestamp(start).tz_convert("UTC").floor("h") if pd.Timestamp(start).tzinfo else pd.Timestamp(start, tz="UTC").floor("h")
    end_h = pd.Timestamp(end).tz_convert("UTC").ceil("h") if pd.Timestamp(end).tzinfo else pd.Timestamp(end, tz="UTC").ceil("h")
    grid = pd.DataFrame(
        {"time": pd.date_range(start_h, end_h, freq="h", tz="UTC", inclusive="left")}
    )
    if grid.empty:
        return grid

    # Coerce every time column to ns precision; parquet roundtrips can demote
    # to [us] which then refuses to merge with [ns] from date_range.
    def _ns(series: pd.Series) -> pd.Series:
        return pd.to_datetime(series, utc=True).astype("datetime64[ns, UTC]")

    grid["time"] = _ns(grid["time"])

    if not dst_res.df.empty:
        dst_df = dst_res.df.copy()
        dst_df["time"] = _ns(dst_df["time"])
        grid = grid.merge(dst_df, on="time", how="left")
    else:
        grid["dst"] = np.nan

    kp_3h = kp_to_3hourly(kp_res.df)
    kp_3h["time"] = _ns(kp_3h["time"])
    grid = pd.merge_asof(
        grid.sort_values("time"),
        kp_3h.sort_values("time"),
        on="time",
        direction="backward",
        tolerance=pd.Timedelta("3h"),
    )

    daily = f107_daily(kp_res.df).rename(columns={"time": "date"})
    daily["date"] = _ns(daily["date"])
    grid["date"] = _ns(grid["time"].dt.floor("D"))
    grid = grid.merge(daily, on="date", how="left")
    return grid.drop(columns="date")


__all__ = [
    "FetchResult",
    "build_space_weather_table",
    "f107_daily",
    "fetch_dst",
    "fetch_kp_ap",
    "kp_to_3hourly",
]
