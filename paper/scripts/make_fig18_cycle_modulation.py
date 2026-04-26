"""Figure 18 — solar-cycle modulation (Q6): rate by solar_cycle_phase quartile."""

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
    q6 = a["Q6_solar_cycle"]
    if q6.get("error") or not q6.get("by_quartile"):
        raise RuntimeError(q6.get("error", "no quartile data"))

    rows = q6["by_quartile"]

    use("agu")
    fig, ax = plt.subplots(figsize=(4.0, 2.6))
    labels = [f"Q{int(r['quartile']) + 1}\n(F10.7 phase {r['phase_lo']:.2f}–{r['phase_hi']:.2f})\nn={int(r['n'])}"
              for r in rows]
    rates = [r["rate_mean"] for r in rows]
    bars = ax.bar(
        labels, rates,
        color=[COLORS["muted"], COLORS["primary"], COLORS["accent"], COLORS["warn"]][: len(rows)],
        width=0.6,
    )
    for bar, v in zip(bars, rates, strict=True):
        ax.annotate(f"{v:.3f}", xy=(bar.get_x() + bar.get_width() / 2, v),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7)
    ax.set_ylabel("EPB-positive rate (per storm)")
    ax.set_title(f"Solar-cycle phase quartile  ·  n_storms = {q6['n_storms']}", fontsize=8)
    fig.tight_layout()
    paths = save_figure(fig, "fig18_cycle_modulation", snapshot_id=snapshot_id, model_id=model_id)
    plt.close(fig)
    for ext, p in paths.items():
        print(f"  {ext.upper()}: {p}")


if __name__ == "__main__":
    main()
