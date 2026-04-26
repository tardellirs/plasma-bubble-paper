"""Figure 13 — Q2 polar plot: EPB rate vs LT-of-Dst-min.

The visual smoking gun for the Pre-Reversal Enhancement (PRE) hypothesis:
storms whose Dst minimum lands in the 17-22 LT window over the Brazilian
sector should produce more EPBs than those that minimise at other LTs.

Polar layout: theta = local time (0..24h), radius = mean per-storm rate
in that LT bin, with the 4 categorical bins (pre_sunset / PRE /
post_midnight / morning) drawn as wedges. CI band rendered as a fan.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _storms_v3_io import load_analysis, save_figure
from _style import COLORS, use

# Centre of each LT bin in hours (UTC-3 for Brazilian sector).
BIN_LT_CENTRE = {
    "pre_sunset": 14.5,    # 12-17
    "PRE": 19.5,           # 17-22  ← PRE window
    "post_midnight": 2.0,  # 22-06 (centre at ~02 LT)
    "morning": 9.0,        # 06-12
}
BIN_LABEL = {
    "pre_sunset": "Pre-sunset",
    "PRE": "PRE 17-22h",
    "post_midnight": "Post-midnight",
    "morning": "Morning",
}


def main(*, snapshot_id: str = "v3", model_id: str = "xgb_v0.3.0", **_: object) -> None:
    a = load_analysis()
    q2 = a["Q2_lt_amplification"]
    four = q2["four_bin"]
    p_2bin = q2["two_bin_mannwhitney_test"]["p_one_sided_greater"]

    use("agu")
    fig = plt.figure(figsize=(4.2, 4.4))
    ax = fig.add_subplot(projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)  # clockwise
    ax.set_xticks(np.linspace(0, 2 * np.pi, 24, endpoint=False))
    ax.set_xticklabels([str(h) if h % 3 == 0 else "" for h in range(24)], fontsize=6)

    rmax = max((v.get("ci_hi", 0) or 0) for v in four.values()) * 1.1 or 0.3
    ax.set_ylim(0, rmax)
    ax.set_yticks(np.linspace(0, rmax, 4))
    ax.set_yticklabels([f"{x:.2f}" for x in np.linspace(0, rmax, 4)], fontsize=5)

    # Highlight PRE wedge (17-22 LT) with a soft band.
    pre_lo = 17 / 24 * 2 * np.pi
    pre_hi = 22 / 24 * 2 * np.pi
    pre_theta = np.linspace(pre_lo, pre_hi, 60)
    ax.fill_between(pre_theta, 0, rmax, color=COLORS["warn"], alpha=0.06)

    # Plot each bin as a wedge with mean dot + CI line.
    for bin_name, info in four.items():
        if info["n"] == 0:
            continue
        theta = (BIN_LT_CENTRE[bin_name] / 24) * 2 * np.pi
        mean = info["mean"]
        lo = info["ci_lo"]
        hi = info["ci_hi"]
        col = COLORS["warn"] if bin_name in ("PRE",) else COLORS["primary"]
        ax.errorbar(
            [theta], [mean],
            yerr=[[mean - lo], [hi - mean]],
            fmt="o", color=col, markersize=7, elinewidth=1.5, capsize=4,
        )
        ax.annotate(
            f"{BIN_LABEL[bin_name]}\nn={info['n']}",
            xy=(theta, mean),
            xytext=(theta, mean + rmax * 0.08),
            ha="center", fontsize=6, color=COLORS["ink"],
        )

    ax.set_title(
        f"EPB rate by LT of Dst-min  ·  Mann-Whitney p={p_2bin:.3f}",
        fontsize=8, pad=12,
    )
    fig.tight_layout()
    paths = save_figure(
        fig,
        "fig13_storm_lt_polar",
        snapshot_id=snapshot_id,
        model_id=model_id,
        extra={"two_bin_p_value": p_2bin},
    )
    plt.close(fig)
    for ext, p in paths.items():
        print(f"  {ext.upper()}: {p}")


if __name__ == "__main__":
    main()
