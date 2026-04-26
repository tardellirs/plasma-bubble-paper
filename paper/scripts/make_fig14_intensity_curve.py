"""Figure 14 — EPB rate vs |Dst|-min intensity (Q3).

Hex-bin the per-storm rate samples on (|Dst|-min, rate); overlay the
quintile means + Spearman rho text annotation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _storms_v3_io import (
    CATALOG_PATH,
    PREDICTIONS_PATH,
    load_analysis,
    save_figure,
)
from _style import COLORS, use


def main(*, snapshot_id: str = "v3", model_id: str = "xgb_v0.3.0", **_: object) -> None:
    a = load_analysis()
    q3 = a["Q3_intensity_curve"]
    if q3.get("error"):
        raise RuntimeError(q3["error"])

    # Recompute the per-storm scatter from predictions parquet for the
    # hex layer (the JSON only carries the bin summaries).
    cat = pd.read_parquet(CATALOG_PATH)
    pred = pd.read_parquet(PREDICTIONS_PATH)
    storms = cat[cat["is_intense_or_stronger"]][["storm_id", "dst_min_value"]].copy()
    storms["abs_dst_min"] = storms["dst_min_value"].abs()
    rate_by_storm = (
        (pred["epb_probability"] >= 0.5)
        .groupby(pred["storm_id"])
        .mean()
        .reset_index(name="rate")
        .merge(storms, on="storm_id")
    )

    use("agu")
    fig, ax = plt.subplots(figsize=(4.2, 3.0))

    if len(rate_by_storm) >= 5:
        ax.scatter(
            rate_by_storm["abs_dst_min"], rate_by_storm["rate"],
            s=18, color=COLORS["primary"], alpha=0.55, label="per storm",
        )

    # Quintile mean line.
    bin_centers = []
    bin_means = []
    for b in q3["bins"]:
        bin_centers.append((b["abs_dst_lo"] + b["abs_dst_hi"]) / 2)
        bin_means.append(b["rate_mean"])
    ax.plot(
        bin_centers, bin_means, "-o", color=COLORS["warn"],
        markersize=5, linewidth=1.5, label="quintile mean",
    )

    ax.set_xlabel("|Dst|-min (nT)")
    ax.set_ylabel("EPB-positive rate (per storm)")
    ax.set_title(
        f"EPB rate vs storm intensity  ·  Spearman ρ = {q3['spearman_rho']:.2f}  "
        f"(p = {q3['spearman_p']:.3f}, n = {q3['n_storms']})",
        fontsize=8,
    )
    ax.legend(loc="best", fontsize=7)
    fig.tight_layout()

    paths = save_figure(
        fig, "fig14_intensity_curve", snapshot_id=snapshot_id, model_id=model_id,
    )
    plt.close(fig)
    for ext, p in paths.items():
        print(f"  {ext.upper()}: {p}")


if __name__ == "__main__":
    main()
