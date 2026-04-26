"""Figure 17 — pre-storm baseline drift (Q5)."""

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
    q5 = a["Q5_pre_storm_baseline"]
    if q5.get("error"):
        raise RuntimeError(q5["error"])

    use("agu")
    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    bars = ax.bar(
        ["Quiet baseline\n(no storm)",
         f"Pre-storm\n−{int(q5['pre_hours'])} h … 0 h",
         "Storm\n(main + recovery)"],
        [q5["quiet_rate"], q5["pre_rate"], a["Q1_storm_vs_quiet"]["storm_rate_mean"]],
        color=[COLORS["muted"], COLORS["accent"], COLORS["warn"]], width=0.55,
    )
    ax.set_ylabel("EPB-positive rate")
    er = q5.get("elevation_ratio", float("nan"))
    title = "Pre-storm baseline drift"
    if er == er:  # not NaN
        title += f"  ·  pre/quiet = {er:.2f}×"
    ax.set_title(title, fontsize=8)
    for bar, v in zip(bars, [q5["quiet_rate"], q5["pre_rate"], a["Q1_storm_vs_quiet"]["storm_rate_mean"]], strict=True):
        ax.annotate(f"{v:.3f}", xy=(bar.get_x() + bar.get_width() / 2, v),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7)
    fig.tight_layout()
    paths = save_figure(fig, "fig17_precursor", snapshot_id=snapshot_id, model_id=model_id)
    plt.close(fig)
    for ext, p in paths.items():
        print(f"  {ext.upper()}: {p}")


if __name__ == "__main__":
    main()
