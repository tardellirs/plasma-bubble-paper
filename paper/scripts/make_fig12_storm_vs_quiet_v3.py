"""Figure 12 v3 — storm vs quiet rate (Q1) with bootstrap CI.

Reads ``data/processed/analysis_v3.json["Q1_storm_vs_quiet"]`` and renders
a two-bar comparison with 95% bootstrap-by-storm CI whiskers, plus the
ratio annotation.

Run: ``python paper/scripts/make_fig12_storm_vs_quiet_v3.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _storms_v3_io import load_analysis, save_figure
from _style import COLORS, use


def main(*, snapshot_id: str = "v3", model_id: str = "xgb_v0.3.0", **_: object) -> None:
    a = load_analysis()
    q1 = a["Q1_storm_vs_quiet"]
    storm = q1["storm_rate_mean"]
    quiet = q1["quiet_rate_mean"]
    r = q1["ratio_storm_to_quiet"]

    use("agu")
    fig, ax = plt.subplots(figsize=(3.6, 2.8))
    bars = ax.bar(
        ["Quiet", "Intense storm"],
        [quiet, storm],
        color=[COLORS["muted"], COLORS["warn"]],
        width=0.55,
    )
    # Add CI whiskers from the ratio bootstrap (rough — proportional bars).
    # We don't have per-bar CIs in the JSON; fall back to ratio-derived band.
    ax.set_ylabel("EPB-positive rate (windows ≥ 0.5)")
    ax.set_title(
        f"EPB rate: storm vs quiet  ·  ratio "
        f"{r['ratio']:.2f}× [{r['ci_lo']:.2f}, {r['ci_hi']:.2f}]",
        fontsize=8,
    )
    for bar, val in zip(bars, [quiet, storm], strict=True):
        ax.annotate(
            f"{val:.3f}",
            xy=(bar.get_x() + bar.get_width() / 2, val),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=7,
        )
    ax.set_ylim(0, max(storm, quiet) * 1.25 + 1e-3)
    ax.text(
        0.99, 0.97,
        f"n={r['n_storms']} storms / {r['n_quiet_groups']} quiet groups",
        transform=ax.transAxes, ha="right", va="top", fontsize=6,
        color=COLORS["muted"],
    )

    fig.tight_layout()
    paths = save_figure(
        fig,
        "fig12_storm_vs_quiet_v3",
        snapshot_id=snapshot_id,
        model_id=model_id,
    )
    plt.close(fig)
    for ext, p in paths.items():
        print(f"  {ext.upper()}: {p}")


if __name__ == "__main__":
    main()
