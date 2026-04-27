"""EPB-risk forecast endpoint (Phase 6.E of the storms-v3 plan).

This is intentionally a *climatological* forecast, not a real-time
prediction: we do not have live ROTI / DTEC ingest. We combine the
current geomagnetic state (Dst/Kp/F10.7 from the cached space-weather
parquet) with the Q6 solar-cycle quartile rates from analysis_v3.json
to produce a coarse risk band ("low / moderate / high / extreme") and
a numeric expected per-window EPB rate. The web `/forecast` page
renders this verbatim with a clear caveat block.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pandas as pd
from fastapi import APIRouter

from epb_detector.config import SETTINGS

router = APIRouter(prefix="/forecast", tags=["forecast"])


_ANALYSIS_PATH = SETTINGS.paths.data_processed / "analysis_v3.json"
_SW_PATH = SETTINGS.paths.data_space_weather / "kp_ap_f107.parquet"


def _quartile_for_phase(quartiles: list[dict], phase: float) -> dict | None:
    """Return the Q6 quartile dict whose [phase_lo, phase_hi] contains ``phase``."""
    if not quartiles or phase is None:
        return None
    for q in quartiles:
        lo = q.get("phase_lo")
        hi = q.get("phase_hi")
        if lo is None or hi is None:
            continue
        if lo <= phase <= hi:
            return q
    # Fall back to nearest by midpoint.
    return min(
        quartiles,
        key=lambda q: abs(((q.get("phase_lo", 0) + q.get("phase_hi", 1)) / 2) - phase),
    )


def _derive_phase_from_f107(f107: float) -> float:
    """Map current F10.7 to a 0–1 cycle phase using the same scaling
    used in the storm-catalog enrichment (rough min ≈ 70 sfu, max ≈ 200).
    """
    f_min, f_max = 65.0, 200.0
    return float(max(0.0, min(1.0, (f107 - f_min) / (f_max - f_min))))


def _risk_band(dst: float | None, predicted_rate: float | None) -> str:
    """Map (current Dst, predicted EPB rate) to a coarse band."""
    if dst is not None and dst <= -250:
        return "extreme"
    if dst is not None and dst <= -100:
        return "high"
    if predicted_rate is not None and predicted_rate >= 0.030:
        return "high"
    if dst is not None and dst <= -50:
        return "moderate"
    if predicted_rate is not None and predicted_rate >= 0.015:
        return "moderate"
    return "low"


@router.get("/epb-risk")
def epb_risk(lookahead_hours: int = 6) -> dict:
    """Climatological EPB risk for the next few hours over the Brazilian
    sector.

    Returns the *current* Dst/Kp/F10.7, the inferred solar-cycle phase,
    the matching Q6 quartile (with its mean per-window rate), and a
    coarse risk band. ``lookahead_hours`` is recorded but not yet used
    — this is a 1-step lookup, not an integrated trajectory.
    """
    available = _ANALYSIS_PATH.exists() and _SW_PATH.exists()
    if not available:
        return {"available": False, "reason": "analysis_v3.json or kp_ap_f107.parquet missing"}

    df = pd.read_parquet(_SW_PATH).sort_values("date")
    if df.empty:
        return {"available": False, "reason": "space-weather parquet empty"}

    # Last row holds today's daily aggregate; for the most-recent Dst we
    # need the hourly grid since Dst is hourly, not daily. Approximate by
    # taking the last F10.7 + the last available daily Ap.
    last = df.iloc[-1]
    f107 = float(last["F107obs"]) if pd.notna(last.get("F107obs")) else float("nan")
    ap_now = float(last["Ap"]) if pd.notna(last.get("Ap")) else None

    # Dst from the merged hourly grid via the existing builder.
    from epb_detector.external import space_weather as sw

    try:
        end = pd.Timestamp(last["date"]).tz_convert("UTC").to_pydatetime() + timedelta(hours=23)
        start = end - timedelta(hours=24)
        grid = sw.build_space_weather_table(start, end)
        if not grid.empty:
            grid = grid.dropna(subset=["dst"]) if "dst" in grid.columns else grid
        if grid.empty:
            dst_now = None
            dst_24h = []
        else:
            dst_now = float(grid["dst"].iloc[-1]) if "dst" in grid.columns else None
            dst_24h = [
                {"time": pd.Timestamp(r["time"]).isoformat(), "dst": float(r["dst"])}
                for r in grid[["time", "dst"]].dropna().to_dict(orient="records")
            ]
    except Exception:
        dst_now = None
        dst_24h = []

    analysis = json.loads(_ANALYSIS_PATH.read_text())
    quartiles = analysis.get("Q6_solar_cycle", {}).get("by_quartile", [])

    cycle_phase = _derive_phase_from_f107(f107) if f107 == f107 else None  # NaN check
    matched_q = _quartile_for_phase(quartiles, cycle_phase) if cycle_phase is not None else None
    predicted_rate = float(matched_q["rate_mean"]) if matched_q else None

    band = _risk_band(dst_now, predicted_rate)

    return {
        "available": True,
        "lookahead_hours": lookahead_hours,
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "current": {
            "time": pd.Timestamp(last["date"]).isoformat(),
            "f107_obs": f107,
            "ap_daily": ap_now,
            "dst_latest_hour": dst_now,
        },
        "cycle": {
            "phase": cycle_phase,
            "matched_quartile": matched_q,
            "all_quartiles": quartiles,
        },
        "predicted_rate_per_window": predicted_rate,
        "risk_band": band,
        "dst_24h": dst_24h,
        "method": "current Dst severity OR climatological per-window rate from Q6 quartile",
    }
