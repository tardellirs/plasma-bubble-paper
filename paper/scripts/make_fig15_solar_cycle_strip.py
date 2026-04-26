"""Figure 15 — 11-year sunspot number strip with storm overlay (Q6 visual).

Top: SSN line spanning 2014–today (from kp_ap_f107.parquet, column SN).
Overlaid: every catalog storm as a dot at (dst_min_time, |dst_min|) on a
mirror y-axis. Vertical bands highlight ingest-coverage periods.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _storms_v3_io import CATALOG_PATH, save_figure
from _style import COLORS, use

from epb_detector.config import SETTINGS

KP_F107_PATH = SETTINGS.paths.data_space_weather / "kp_ap_f107.parquet"


def main(*, snapshot_id: str = "v3", model_id: str = "xgb_v0.3.0", **_: object) -> None:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Missing {CATALOG_PATH}")
    if not KP_F107_PATH.exists():
        raise FileNotFoundError(
            f"Missing {KP_F107_PATH} — run any `epb labels v2` once to populate the cache."
        )

    cat = pd.read_parquet(CATALOG_PATH)
    sw = pd.read_parquet(KP_F107_PATH)
    sw["date"] = pd.to_datetime(sw["date"], utc=True)
    sw = sw.sort_values("date")
    sw = sw[(sw["date"] >= "2014-01-01") & (sw["date"] <= "2025-01-01")]

    use("agu")
    fig, ax_top = plt.subplots(figsize=(7.0, 2.6))

    # SSN line
    ax_top.plot(
        sw["date"], sw["SN"],
        color=COLORS["primary"], linewidth=0.7, alpha=0.9, label="Sunspot number",
    )
    ax_top.set_ylabel("SSN", color=COLORS["primary"])
    ax_top.tick_params(axis="y", labelcolor=COLORS["primary"])
    ax_top.set_xlim(pd.Timestamp("2014-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"))

    # Mirror axis: storm |Dst|-min as scatter dots
    ax_dst = ax_top.twinx()
    ax_dst.spines["top"].set_visible(False)
    ax_dst.invert_yaxis()
    cat["dst_min_time"] = pd.to_datetime(cat["dst_min_time"], utc=True)
    intense_mask = cat["is_intense_or_stronger"]
    moderate = cat[~intense_mask]
    intense = cat[intense_mask]
    if not moderate.empty:
        ax_dst.scatter(
            moderate["dst_min_time"], moderate["dst_min_value"].abs(),
            s=10, color=COLORS["muted"], alpha=0.4, label="Moderate", zorder=2,
        )
    ax_dst.scatter(
        intense["dst_min_time"], intense["dst_min_value"].abs(),
        s=22, color=COLORS["warn"], alpha=0.85, label="|Dst|≥100", zorder=3,
    )
    ax_dst.set_ylabel("|Dst|-min (nT)", color=COLORS["warn"])
    ax_dst.tick_params(axis="y", labelcolor=COLORS["warn"])
    # Cap y so super-storms don't squash the rest visually.
    ax_dst.set_ylim(420, 0)

    # Ingest coverage bars (Phase 2-A + storm-stratified bursts).
    # Phase 2-A: 2023-09-02 → 2024-05-15
    coverage = [(pd.Timestamp("2023-09-02", tz="UTC"), pd.Timestamp("2024-05-15", tz="UTC"), "P2-A")]
    for lo, hi, _ in coverage:
        ax_top.axvspan(lo, hi, color=COLORS["accent"], alpha=0.07, zorder=1)
    ax_top.text(
        coverage[0][0], ax_top.get_ylim()[1] * 0.92, "  Phase 2-A coverage",
        fontsize=6, color=COLORS["accent"],
    )

    ax_top.set_title(
        "Solar-cycle context — SSN, geomagnetic storms, GNSS coverage",
        fontsize=8,
    )
    fig.legend(
        loc="upper center", ncol=3, frameon=False, fontsize=6,
        bbox_to_anchor=(0.5, 1.02),
    )
    fig.tight_layout()

    paths = save_figure(
        fig, "fig15_solar_cycle_strip", snapshot_id=snapshot_id, model_id=model_id,
    )
    plt.close(fig)
    for ext, p in paths.items():
        print(f"  {ext.upper()}: {p}")


if __name__ == "__main__":
    main()
