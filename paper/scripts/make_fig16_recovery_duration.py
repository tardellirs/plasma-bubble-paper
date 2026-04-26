"""Figure 16 — recovery-duration effect (Q4): short vs long recovery rate."""

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
    q4 = a["Q4_recovery_duration"]
    if q4.get("error"):
        raise RuntimeError(q4["error"])

    use("agu")
    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    bars = ax.bar(
        [f"Short (≤24 h)\nn={q4.get('n_short', 0)}",
         f"Long (≥72 h)\nn={q4.get('n_long', 0)}"],
        [q4.get("short_rate_mean", 0), q4.get("long_rate_mean", 0)],
        color=[COLORS["primary"], COLORS["accent"]], width=0.55,
    )
    ax.set_ylabel("Recovery-phase EPB rate")
    p = q4.get("p_two_sided")
    title = "Recovery duration vs EPB rate"
    if p is not None and p == p:  # not NaN
        title += f"  ·  p={p:.3f}"
    ax.set_title(title, fontsize=8)
    for bar, v in zip(bars, [q4.get("short_rate_mean", 0), q4.get("long_rate_mean", 0)], strict=True):
        ax.annotate(f"{v:.3f}", xy=(bar.get_x() + bar.get_width() / 2, v),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7)
    fig.tight_layout()
    paths = save_figure(fig, "fig16_recovery_duration", snapshot_id=snapshot_id, model_id=model_id)
    plt.close(fig)
    for ext, p in paths.items():
        print(f"  {ext.upper()}: {p}")


if __name__ == "__main__":
    main()
