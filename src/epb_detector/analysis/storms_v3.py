"""Storm-stratified statistical analyses (Q1–Q7 of the storms-v3 plan).

All public functions take a predictions parquet path + the storm catalog
path and return a JSON-serialisable dict that the API + the report inline
verbatim. The shapes are stable so the frontend can render them directly.

Bootstrap convention
--------------------
- For storm-side stats we resample **storm_id** with replacement; each
  storm contributes its windows en bloc to the resampled set. This avoids
  the pseudoreplication that a per-window bootstrap would introduce.
- For quiet-side stats we resample (station, calendar-day) — same
  rationale.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_intense_storm(catalog: pd.DataFrame) -> set[int]:
    """Storm IDs whose ``is_intense_or_stronger`` flag is set."""
    if "is_intense_or_stronger" not in catalog.columns:
        return set()
    return set(catalog.loc[catalog["is_intense_or_stronger"], "storm_id"].astype(int))


def _attach_storm_meta(
    df: pd.DataFrame, catalog: pd.DataFrame, cols: Iterable[str]
) -> pd.DataFrame:
    """Left-join selected catalog columns onto a window-level frame by storm_id."""
    if df.empty:
        return df
    sub = catalog[["storm_id", *cols]].drop_duplicates("storm_id")
    return df.merge(sub, on="storm_id", how="left")


def _bootstrap_ratio(
    pos_groups: list[float],
    neg_groups: list[float],
    *,
    n_boot: int = 1000,
    seed: int = 0,
) -> dict[str, float]:
    """Bootstrap the ratio of two group means.

    ``pos_groups`` and ``neg_groups`` carry per-group rates (one rate per
    storm_id for storm-side, one per (sta, day) for quiet-side). The point
    estimate is mean(pos) / mean(neg); CI is from resampling each list
    independently with replacement.
    """
    rng = np.random.default_rng(seed)
    pos = np.asarray(pos_groups, dtype="float64")
    neg = np.asarray(neg_groups, dtype="float64")
    if len(pos) == 0 or len(neg) == 0:
        return {"ratio": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan")}

    point = float(np.mean(pos)) / float(max(np.mean(neg), 1e-9))
    ratios = np.empty(n_boot)
    for i in range(n_boot):
        p = pos[rng.integers(0, len(pos), size=len(pos))]
        n = neg[rng.integers(0, len(neg), size=len(neg))]
        ratios[i] = float(np.mean(p)) / float(max(np.mean(n), 1e-9))
    return {
        "ratio": float(point),
        "ci_lo": float(np.quantile(ratios, 0.025)),
        "ci_hi": float(np.quantile(ratios, 0.975)),
        "n_storms": len(pos),
        "n_quiet_groups": len(neg),
    }


def _rate_per_storm(
    pred: pd.DataFrame,
    storm_ids: set[int],
    *,
    threshold: float = 0.5,
    night_only: bool = True,
) -> list[float]:
    """Per-storm EPB-positive rate (windows with prob ≥ threshold during the storm)."""
    df = pred[pred["storm_id"].isin(storm_ids)]
    if df.empty:
        return []
    if night_only and "local_time_mean" in df.columns:
        df = df[(df["local_time_mean"] >= 19) | (df["local_time_mean"] <= 6)]
    rates = (
        (df["epb_probability"] >= threshold)
        .groupby(df["storm_id"])
        .mean()
        .astype("float64")
        .tolist()
    )
    return rates


def _rate_per_quiet_day(
    pred: pd.DataFrame,
    *,
    threshold: float = 0.5,
    night_only: bool = True,
) -> list[float]:
    """Per (station, day) EPB-positive rate during quiet (no storm) windows."""
    df = pred[pred["storm_id"].fillna(0) == 0]
    if df.empty:
        return []
    if night_only and "local_time_mean" in df.columns:
        df = df[(df["local_time_mean"] >= 19) | (df["local_time_mean"] <= 6)]
    df = df.assign(
        _day=pd.to_datetime(df["window_start"], utc=True).dt.date.astype(str)
    )
    rates = (
        (df["epb_probability"] >= threshold)
        .groupby([df["sta"], df["_day"]])
        .mean()
        .astype("float64")
        .tolist()
    )
    return rates


# ---------------------------------------------------------------------------
# Q1 — % storm vs quiet
# ---------------------------------------------------------------------------


def q1_storm_vs_quiet(
    pred: pd.DataFrame,
    catalog: pd.DataFrame,
    *,
    threshold: float = 0.5,
    night_only: bool = True,
    n_boot: int = 1000,
) -> dict:
    """Storm-time vs quiet-time EPB-positive rate, with bootstrap CI.

    Headline numbers for the /storms gauge + paper fig12.
    """
    intense_ids = _is_intense_storm(catalog)
    storm_rates = _rate_per_storm(
        pred, intense_ids, threshold=threshold, night_only=night_only
    )
    quiet_rates = _rate_per_quiet_day(
        pred, threshold=threshold, night_only=night_only
    )
    storm_mean = float(np.mean(storm_rates)) if storm_rates else float("nan")
    quiet_mean = float(np.mean(quiet_rates)) if quiet_rates else float("nan")
    ratio = _bootstrap_ratio(storm_rates, quiet_rates, n_boot=n_boot)
    return {
        "storm_threshold_nt": -100,
        "epb_threshold": threshold,
        "night_only": night_only,
        "storm_rate_mean": storm_mean,
        "quiet_rate_mean": quiet_mean,
        "ratio_storm_to_quiet": ratio,
        "n_intense_storms": len(intense_ids),
    }


# ---------------------------------------------------------------------------
# Q2 — LT amplification near sunset
# ---------------------------------------------------------------------------


def q2_lt_amplification(
    pred: pd.DataFrame,
    catalog: pd.DataFrame,
    *,
    threshold: float = 0.5,
    night_only: bool = True,
    n_boot: int = 1000,
) -> dict:
    """EPB rate stratified by Dst-minimum LT-at-Brazil bin.

    Both 4-bin descriptive and 2-bin (PRE-adjacent vs non-PRE) test.
    """
    from scipy.stats import kruskal, mannwhitneyu

    intense_cat = catalog[catalog["is_intense_or_stronger"]]
    if intense_cat.empty:
        return {"error": "no intense storms"}

    pred_storm = pred[pred["storm_id"].isin(intense_cat["storm_id"])].copy()
    pred_storm = _attach_storm_meta(pred_storm, intense_cat, ["lt_bin"])
    if night_only and "local_time_mean" in pred_storm.columns:
        pred_storm = pred_storm[
            (pred_storm["local_time_mean"] >= 19)
            | (pred_storm["local_time_mean"] <= 6)
        ]

    # Per-storm rate so each storm = 1 sample.
    rate_by_storm = (
        (pred_storm["epb_probability"] >= threshold)
        .groupby([pred_storm["storm_id"], pred_storm["lt_bin"]])
        .mean()
        .reset_index(name="rate")
    )

    bins_4 = ["pre_sunset", "PRE", "post_midnight", "morning"]
    series_per_bin: dict[str, list[float]] = {
        b: rate_by_storm.loc[rate_by_storm["lt_bin"] == b, "rate"].astype(float).tolist()
        for b in bins_4
    }

    rng = np.random.default_rng(42)

    def _boot_ci(values: list[float]) -> dict:
        if not values:
            return {"mean": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"), "n": 0}
        arr = np.asarray(values, dtype="float64")
        boots = np.array(
            [arr[rng.integers(0, len(arr), size=len(arr))].mean() for _ in range(n_boot)]
        )
        return {
            "mean": float(arr.mean()),
            "ci_lo": float(np.quantile(boots, 0.025)),
            "ci_hi": float(np.quantile(boots, 0.975)),
            "n": len(arr),
        }

    four_bin = {b: _boot_ci(series_per_bin[b]) for b in bins_4}

    # 2-bin: PRE-adjacent (pre_sunset + PRE) vs non-PRE (post_midnight + morning)
    pre_adj = series_per_bin["pre_sunset"] + series_per_bin["PRE"]
    non_pre = series_per_bin["post_midnight"] + series_per_bin["morning"]
    two_bin = {
        "PRE_adjacent": _boot_ci(pre_adj),
        "non_PRE": _boot_ci(non_pre),
    }
    if pre_adj and non_pre:
        u, p = mannwhitneyu(pre_adj, non_pre, alternative="greater")
        two_bin_test = {"mannwhitney_U": float(u), "p_one_sided_greater": float(p)}
    else:
        two_bin_test = {"mannwhitney_U": float("nan"), "p_one_sided_greater": float("nan")}

    populated = [v for v in series_per_bin.values() if len(v) >= 3]
    if len(populated) >= 2:
        h, p = kruskal(*populated)
        kw_test = {"kruskal_H": float(h), "p": float(p), "n_bins": len(populated)}
    else:
        kw_test = {"kruskal_H": float("nan"), "p": float("nan"), "n_bins": len(populated)}

    return {
        "epb_threshold": threshold,
        "night_only": night_only,
        "four_bin": four_bin,
        "two_bin": two_bin,
        "two_bin_mannwhitney_test": two_bin_test,
        "kruskal_wallis_4bin": kw_test,
    }


# ---------------------------------------------------------------------------
# Q3 — intensity response curve
# ---------------------------------------------------------------------------


def q3_intensity_curve(
    pred: pd.DataFrame,
    catalog: pd.DataFrame,
    *,
    threshold: float = 0.5,
    n_boot: int = 1000,
) -> dict:
    """EPB rate vs |Dst|-min, returned as quintile bins + Spearman ρ."""
    from scipy.stats import spearmanr

    storms = catalog[["storm_id", "dst_min_value"]].copy()
    storms["abs_dst_min"] = storms["dst_min_value"].abs()

    pred_storm = pred[pred["storm_id"].isin(storms["storm_id"])].copy()
    rate_by_storm = (
        (pred_storm["epb_probability"] >= threshold)
        .groupby(pred_storm["storm_id"])
        .mean()
        .reset_index(name="rate")
        .merge(storms, on="storm_id")
    )
    if rate_by_storm.empty:
        return {"error": "no data"}

    rho, p = spearmanr(rate_by_storm["abs_dst_min"], rate_by_storm["rate"])

    # Quintile bins (or as many as data allows).
    n = len(rate_by_storm)
    n_bins = min(5, max(2, n // 5))
    rate_by_storm["bin"] = pd.qcut(
        rate_by_storm["abs_dst_min"], q=n_bins, duplicates="drop"
    )
    bins_out = []
    for label, sub in rate_by_storm.groupby("bin"):
        bins_out.append(
            {
                "abs_dst_lo": float(label.left),
                "abs_dst_hi": float(label.right),
                "n": len(sub),
                "rate_mean": float(sub["rate"].mean()),
                "rate_std": float(sub["rate"].std()),
            }
        )
    return {
        "epb_threshold": threshold,
        "n_storms": int(n),
        "spearman_rho": float(rho),
        "spearman_p": float(p),
        "bins": bins_out,
    }


# ---------------------------------------------------------------------------
# Q4 — recovery duration effect
# ---------------------------------------------------------------------------


def q4_recovery_duration(
    pred: pd.DataFrame,
    catalog: pd.DataFrame,
    *,
    threshold: float = 0.5,
    short_hours: float = 24.0,
    long_hours: float = 72.0,
) -> dict:
    """Compare per-storm EPB rate during recovery for short vs long recoveries."""
    from scipy.stats import mannwhitneyu

    sub = catalog[
        catalog["is_intense_or_stronger"] & catalog["recovery_duration_hours"].notna()
    ].copy()
    pred_rec = pred[
        (pred["storm_id"].isin(sub["storm_id"]))
        & (pred["storm_phase"] == "recovery")
    ].copy()
    if pred_rec.empty:
        return {"error": "no recovery windows"}

    rates = (
        (pred_rec["epb_probability"] >= threshold)
        .groupby(pred_rec["storm_id"])
        .mean()
        .reset_index(name="rate")
        .merge(sub[["storm_id", "recovery_duration_hours"]], on="storm_id")
    )
    short = rates[rates["recovery_duration_hours"] <= short_hours]["rate"].tolist()
    longg = rates[rates["recovery_duration_hours"] >= long_hours]["rate"].tolist()
    if len(short) < 2 or len(longg) < 2:
        return {
            "n_short": len(short),
            "n_long": len(longg),
            "short_rate_mean": float(np.mean(short)) if short else float("nan"),
            "long_rate_mean": float(np.mean(longg)) if longg else float("nan"),
            "test": "skipped (n<2 in one group)",
        }
    u, p = mannwhitneyu(short, longg, alternative="two-sided")
    return {
        "n_short": len(short),
        "n_long": len(longg),
        "short_rate_mean": float(np.mean(short)),
        "long_rate_mean": float(np.mean(longg)),
        "mannwhitney_U": float(u),
        "p_two_sided": float(p),
    }


# ---------------------------------------------------------------------------
# Q5 — pre-storm baseline drift
# ---------------------------------------------------------------------------


def q5_pre_storm_baseline(
    pred: pd.DataFrame,
    catalog: pd.DataFrame,
    *,
    threshold: float = 0.5,
    pre_hours: float = 12.0,
) -> dict:
    """Average rate in [-pre_hours, 0] before main_start, vs quiet baseline."""
    intense_ids = _is_intense_storm(catalog)
    if "hours_from_dst_min" not in pred.columns:
        return {"error": "missing hours_from_dst_min"}

    sub = pred[pred["storm_id"].isin(intense_ids)].copy()
    # Hours from main_start = hours_from_dst_min minus the storm's main duration.
    cat = catalog.copy()
    cat["main_duration_hours"] = (
        (pd.to_datetime(cat["dst_min_time"], utc=True)
         - pd.to_datetime(cat["main_start"], utc=True)).dt.total_seconds() / 3600.0
    )
    sub = sub.merge(
        cat[["storm_id", "main_duration_hours"]], on="storm_id", how="left"
    )
    sub["hours_from_main_start"] = (
        sub["hours_from_dst_min"] + sub["main_duration_hours"]
    )

    pre = sub[
        (sub["hours_from_main_start"] >= -pre_hours)
        & (sub["hours_from_main_start"] < 0)
    ]
    pre_rate = float((pre["epb_probability"] >= threshold).mean()) if not pre.empty else float("nan")

    quiet = pred[pred["storm_id"].fillna(0) == 0]
    quiet_rate = float((quiet["epb_probability"] >= threshold).mean()) if not quiet.empty else float("nan")

    return {
        "pre_hours": pre_hours,
        "n_pre_windows": len(pre),
        "pre_rate": pre_rate,
        "quiet_rate": quiet_rate,
        "elevation_ratio": float(pre_rate / quiet_rate) if quiet_rate > 0 else float("nan"),
    }


# ---------------------------------------------------------------------------
# Q6 — solar-cycle modulation
# ---------------------------------------------------------------------------


def q6_solar_cycle(
    pred: pd.DataFrame,
    catalog: pd.DataFrame,
    *,
    threshold: float = 0.5,
) -> dict:
    """Same intensity class, different solar-cycle phase quartile → rate ratio."""
    sub = catalog[
        catalog["is_intense_or_stronger"] & catalog["solar_cycle_phase"].notna()
    ].copy()
    if sub.empty:
        return {"error": "no solar_cycle_phase data"}

    sub["phase_q"] = pd.qcut(sub["solar_cycle_phase"], q=4, duplicates="drop", labels=False)
    pred_storm = pred[pred["storm_id"].isin(sub["storm_id"])].copy()
    rate_by_storm = (
        (pred_storm["epb_probability"] >= threshold)
        .groupby(pred_storm["storm_id"])
        .mean()
        .reset_index(name="rate")
        .merge(sub[["storm_id", "phase_q", "solar_cycle_phase"]], on="storm_id")
    )

    out = []
    for q in sorted(rate_by_storm["phase_q"].dropna().unique()):
        chunk = rate_by_storm[rate_by_storm["phase_q"] == q]
        out.append(
            {
                "quartile": int(q),
                "n": len(chunk),
                "phase_lo": float(chunk["solar_cycle_phase"].min()),
                "phase_hi": float(chunk["solar_cycle_phase"].max()),
                "rate_mean": float(chunk["rate"].mean()),
            }
        )
    return {"epb_threshold": threshold, "by_quartile": out, "n_storms": len(rate_by_storm)}


# ---------------------------------------------------------------------------
# Q7 — inter-station correlation lag
# ---------------------------------------------------------------------------


def q7_inter_station_lag(
    pred: pd.DataFrame,
    catalog: pd.DataFrame,
    *,
    threshold: float = 0.5,
    pair: tuple[str, str] = ("SALU", "BRAZ"),
    max_lag_min: int = 60,
    bin_min: int = 10,
) -> dict:
    """Cross-correlation of EPB-positive rate between two stations, within
    intense-storm windows, lag-binned in 10-min steps.
    """
    intense_ids = _is_intense_storm(catalog)
    sub = pred[pred["storm_id"].isin(intense_ids)].copy()
    if sub.empty:
        return {"error": "no intense-storm predictions"}
    sub["t"] = pd.to_datetime(sub["window_start"], utc=True)
    sub = sub.set_index("t").sort_index()

    a = sub[sub["sta"] == pair[0]]["epb_probability"].ge(threshold).astype(float).resample(f"{bin_min}min").mean()
    b = sub[sub["sta"] == pair[1]]["epb_probability"].ge(threshold).astype(float).resample(f"{bin_min}min").mean()
    if a.empty or b.empty:
        return {"error": f"no data for one of {pair}"}

    a, b = a.align(b, fill_value=0.0)
    a_z = (a - a.mean()) / max(a.std(), 1e-9)
    b_z = (b - b.mean()) / max(b.std(), 1e-9)

    lags_min = list(range(-max_lag_min, max_lag_min + 1, bin_min))
    corrs = []
    for lag in lags_min:
        shift = lag // bin_min
        if shift > 0:
            c = float((a_z.iloc[shift:].values * b_z.iloc[:-shift].values).mean())
        elif shift < 0:
            c = float((a_z.iloc[:shift].values * b_z.iloc[-shift:].values).mean())
        else:
            c = float((a_z.values * b_z.values).mean())
        corrs.append({"lag_min": lag, "corr": c})
    peak = max(corrs, key=lambda r: r["corr"])
    return {
        "pair": list(pair),
        "bin_minutes": bin_min,
        "epb_threshold": threshold,
        "peak_lag_min": peak["lag_min"],
        "peak_corr": peak["corr"],
        "lags": corrs,
    }


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def run_all(
    predictions_path: Path,
    catalog_path: Path,
    *,
    out_path: Path,
    threshold: float = 0.5,
    n_boot: int = 1000,
) -> dict:
    pred = pd.read_parquet(predictions_path)
    cat = pd.read_parquet(catalog_path)
    out = {
        "model_id_predicted_with": "(set by caller)",
        "predictions_path": str(predictions_path),
        "catalog_path": str(catalog_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "Q1_storm_vs_quiet": q1_storm_vs_quiet(pred, cat, threshold=threshold, n_boot=n_boot),
        "Q2_lt_amplification": q2_lt_amplification(pred, cat, threshold=threshold, n_boot=n_boot),
        "Q3_intensity_curve": q3_intensity_curve(pred, cat, threshold=threshold, n_boot=n_boot),
        "Q4_recovery_duration": q4_recovery_duration(pred, cat, threshold=threshold),
        "Q5_pre_storm_baseline": q5_pre_storm_baseline(pred, cat, threshold=threshold),
        "Q6_solar_cycle": q6_solar_cycle(pred, cat, threshold=threshold),
        "Q7_inter_station_lag": q7_inter_station_lag(pred, cat, threshold=threshold),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))
    return out
