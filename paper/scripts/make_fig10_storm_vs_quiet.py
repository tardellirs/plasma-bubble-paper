"""Figure 10 — storm vs quiet detection rate and PR curves.

Splits the v1 snapshot by ``storm_phase`` and shows:

  Top : EPB-positive rate (per 10-min window) for {quiet, recovery, main}.
  Bottom: PR curves (model probability) for storm vs quiet, with bootstrap IC.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _style import COLORS, use  # noqa: E402

from epb_detector.config import SETTINGS  # noqa: E402
from epb_detector.models import xgb as xgb_model  # noqa: E402

REPO = SETTINGS.paths.repo_root
FIG_DIR = SETTINGS.paths.paper_figures
MANIFEST = FIG_DIR / "manifest.json"


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(snapshot_id: str = "v1") -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    snap = SETTINGS.paths.data_snapshots / snapshot_id
    feats = pd.read_parquet(snap / "features.parquet")
    labels = pd.read_parquet(snap / "labels.parquet")
    full = pd.read_parquet(SETTINGS.paths.data_processed / f"labels_{snapshot_id}.parquet")
    proba = xgb_model.predict_proba(full, "xgb_v0.2.0")
    return full, full["label"].astype(int).to_numpy(), proba


def _bootstrap_pr(y: np.ndarray, p: np.ndarray, n: int = 200, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    common_recall = np.linspace(0, 1, 100)
    precisions = np.zeros((n, common_recall.size))
    for i in range(n):
        idx = rng.integers(0, len(y), size=len(y))
        if y[idx].sum() < 5:
            continue
        prec, rec, _ = precision_recall_curve(y[idx], p[idx])
        precisions[i] = np.interp(common_recall, rec[::-1], prec[::-1])
    lo = np.percentile(precisions, 2.5, axis=0)
    hi = np.percentile(precisions, 97.5, axis=0)
    med = np.median(precisions, axis=0)
    return {"recall": common_recall, "median": med, "lo": lo, "hi": hi}


def _render(snapshot_id: str = "v1") -> dict[str, Path]:
    df, y, p = _load(snapshot_id)

    use("agu")
    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(8.0, 3.4))

    # --- Panel 1: positive-rate per phase
    ax = axes[0]
    rates = (
        df.groupby("storm_phase")["label"]
        .agg(["count", "sum"])
        .rename(columns={"count": "n", "sum": "pos"})
    )
    rates["rate"] = rates["pos"] / rates["n"] * 100
    order = ["none", "main", "recovery"]
    rates = rates.reindex([o for o in order if o in rates.index])
    palette = {
        "none": COLORS["primary"],
        "main": COLORS["warn"],
        "recovery": COLORS["accent"],
    }
    bars = ax.bar(rates.index, rates["rate"], color=[palette[i] for i in rates.index])
    for bar, n in zip(bars, rates["n"], strict=True):
        ax.annotate(
            f"n={n:,}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=7,
            color=COLORS["muted"],
        )
    ax.set_ylabel("EPB-positive rate [%]")
    ax.set_xlabel("Storm phase (Dst classification)")
    ax.set_title("Detection rate by storm phase", loc="left")

    # --- Panel 2: PR curves with bootstrap
    ax = axes[1]
    quiet_mask = df["storm_phase"] == "none"
    storm_mask = ~quiet_mask
    for label, mask, color in (
        ("Quiet", quiet_mask, COLORS["primary"]),
        ("Storm (main+recovery)", storm_mask, COLORS["warn"]),
    ):
        if mask.sum() < 200:
            continue
        bs = _bootstrap_pr(y[mask.to_numpy()], p[mask.to_numpy()])
        ax.plot(bs["recall"], bs["median"], color=color, label=label, linewidth=1.4)
        ax.fill_between(
            bs["recall"], bs["lo"], bs["hi"], color=color, alpha=0.18, linewidth=0
        )
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_title("Storm vs quiet — PR with 95% bootstrap CI", loc="left")
    ax.legend(loc="lower left")

    fig.suptitle("Storm-time vs quiet-time EPB detection", fontsize=10, x=0.01, ha="left")
    fig.tight_layout()

    out = {
        "pdf": FIG_DIR / "fig10_storm_vs_quiet.pdf",
        "png": FIG_DIR / "fig10_storm_vs_quiet.png",
    }
    for path in out.values():
        fig.savefig(path)
    plt.close(fig)
    return out


def _update_manifest(paths: dict[str, Path], snapshot_id: str) -> None:
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"figures": {}}
    manifest.setdefault("figures", {})["fig10_storm_vs_quiet"] = {
        "script": "paper/scripts/make_fig10_storm_vs_quiet.py",
        "snapshot_id": snapshot_id,
        "model_id": "xgb_v0.2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": {ext: str(p.relative_to(REPO)) for ext, p in paths.items()},
        "sha256": {ext: _file_sha256(p) for ext, p in paths.items()},
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def main(*, snapshot_id: str = "v1", **_: object) -> None:
    paths = _render(snapshot_id)
    _update_manifest(paths, snapshot_id)
    for ext, p in paths.items():
        print(f"  {ext.upper()}: {p}")


if __name__ == "__main__":
    main()
