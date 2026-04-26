"""Figure 19 — inter-station lag correlation (Q7)."""

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
    q7 = a["Q7_inter_station_lag"]
    if q7.get("error"):
        raise RuntimeError(q7["error"])

    lags = [r["lag_min"] for r in q7["lags"]]
    corrs = [r["corr"] for r in q7["lags"]]

    use("agu")
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    ax.plot(lags, corrs, "-o", color=COLORS["primary"], markersize=4)
    ax.axvline(0, color=COLORS["muted"], linewidth=0.8, linestyle="--", alpha=0.6)
    ax.axvline(q7["peak_lag_min"], color=COLORS["warn"], linewidth=1.0,
               linestyle=":", label=f"peak @ {q7['peak_lag_min']:+d} min")
    ax.set_xlabel(f"{q7['pair'][0]} lag relative to {q7['pair'][1]} (minutes)")
    ax.set_ylabel("Cross-correlation")
    ax.set_title(
        f"Inter-station EPB rate correlation  ·  intense storms only  "
        f"(bin = {q7['bin_minutes']} min)",
        fontsize=8,
    )
    ax.legend(loc="best", fontsize=7)
    fig.tight_layout()
    paths = save_figure(fig, "fig19_station_lag", snapshot_id=snapshot_id, model_id=model_id)
    plt.close(fig)
    for ext, p in paths.items():
        print(f"  {ext.upper()}: {p}")


if __name__ == "__main__":
    main()
