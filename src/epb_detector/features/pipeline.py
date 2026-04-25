"""Feature builder: ROTI / DTEC / SIDX → wide window-level table.

Inputs come from :mod:`epb_detector.io.readers`. The output frame has one row
per (sta, sat, window_start) and is partitioned by year/month/sta when
written to parquet via :func:`write_features`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from epb_detector.config import SETTINGS
from epb_detector.features import geometric, statistics, windows
from epb_detector.io import readers


def _per_satellite_frame(roti_df: pd.DataFrame) -> dict[tuple[str, str], pd.DataFrame]:
    """Group a ROTI dataframe by (STA, SAT)."""
    return {
        (str(sta), str(sat)): g.reset_index(drop=True)
        for (sta, sat), g in roti_df.groupby(["STA", "SAT"], sort=False)
    }


def build_features(
    roti_df: pd.DataFrame,
    *,
    dtec_df: pd.DataFrame | None = None,
    sidx_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build window-level features across all satellites in ``roti_df``.

    DTEC/SIDX are merged on (SAT, time) when supplied; missing series produce
    NaN-filled columns so the schema is stable.
    """
    cfg = SETTINGS.features
    rule_thr = SETTINGS.labels.roti_threshold_tecu_per_min
    rows: list[dict[str, object]] = []
    if roti_df.empty:
        return pd.DataFrame()

    dtec_idx = (
        dtec_df.set_index(["SAT", "time"])["DTEC"].sort_index() if dtec_df is not None else None
    )
    sidx_idx = (
        sidx_df.set_index(["SAT", "time"])["SIDX"].sort_index() if sidx_df is not None else None
    )

    for (sta, sat), arc_df in _per_satellite_frame(roti_df).items():
        wins = windows.make_windows(arc_df, sta=sta, sat=sat)
        for w in wins:
            t = w.samples["time"]
            roti = w.samples["ROTI"]
            elev = w.samples["Elevation"]
            lon = w.samples["Longitude"]
            lat = w.samples["Latitude"]

            roti_feat = statistics.roti_features(t, roti, threshold_tecu_per_min=rule_thr)
            geo_feat = geometric.geometric_features(t, lon, lat, elev)

            if dtec_idx is not None:
                try:
                    dtec_chunk = dtec_idx.loc[(sat, slice(w.start, w.end))].droplevel("SAT")
                except KeyError:
                    dtec_chunk = pd.Series(dtype="float64")
                dtec_feat = statistics.dtec_features(
                    pd.Series(dtec_chunk.index), pd.Series(dtec_chunk.to_numpy())
                )
            else:
                dtec_feat = {"dtec_max": float("nan"), "dtec_p95": float("nan"),
                             "dtec_std": float("nan"), "dtec_slope": float("nan")}

            if sidx_idx is not None:
                try:
                    sidx_chunk = sidx_idx.loc[(sat, slice(w.start, w.end))].droplevel("SAT")
                except KeyError:
                    sidx_chunk = pd.Series(dtype="float64")
                sidx_feat = statistics.sidx_features(pd.Series(sidx_chunk.to_numpy()))
            else:
                sidx_feat = {"sidx_max": float("nan"), "sidx_mean": float("nan")}

            rows.append(
                {
                    "sta": sta,
                    "sat": sat,
                    "window_start": w.start,
                    "window_end": w.end,
                    "window_minutes": cfg.window_minutes,
                    **roti_feat,
                    **dtec_feat,
                    **sidx_feat,
                    **geo_feat,
                }
            )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values(["sta", "sat", "window_start"]).reset_index(drop=True)
    return df


def build_for_station_day(station_dir: Path, sta: str, year: int, doy: int) -> pd.DataFrame:
    """Build features for one pyOASIS output dir, both GPS and GLONASS combined."""
    parts = []
    for system in ("G", "R"):
        roti_path = station_dir / f"{sta}_{doy:03d}_{year}_{system}_ROTI.txt"
        if not roti_path.exists():
            continue
        roti = readers.read_roti(roti_path)
        dtec_path = station_dir / f"{sta}_{doy:03d}_{year}_{system}_DTEC.txt"
        sidx_path = station_dir / f"{sta}_{doy:03d}_{year}_{system}_SIDX.txt"
        dtec = readers.read_dtec(dtec_path) if dtec_path.exists() else None
        sidx = readers.read_sidx(sidx_path) if sidx_path.exists() else None
        feats = build_features(roti, dtec_df=dtec, sidx_df=sidx)
        if not feats.empty:
            feats["constellation"] = system
            feats["year"] = year
            feats["doy"] = doy
            parts.append(feats)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def write_features(df: pd.DataFrame, out_root: Path | None = None) -> Path:
    """Persist a wide feature frame partitioned by year/month/sta."""
    out = out_root or SETTINGS.paths.data_processed / "features"
    out.mkdir(parents=True, exist_ok=True)
    df = df.copy()
    df["year"] = df["window_start"].dt.year
    df["month"] = df["window_start"].dt.month
    df.to_parquet(out, index=False, partition_cols=["year", "month", "sta"])
    return out
