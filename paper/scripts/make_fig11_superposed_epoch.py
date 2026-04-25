"""Figure 11 — superposed-epoch analysis around Dst minimum.

Aligns every detected storm at its Dst-minimum epoch (t = 0). For each hour
in [-48, +48], computes the EPB-positive rate (per 10-min window across all
station-days that overlapped the storm). Shows median + 95% bootstrap IC.
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

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _style import COLORS, use  # noqa: E402

from epb_detector.config import SETTINGS  # noqa: E402

FIG_DIR = SETTINGS.paths.paper_figures
MANIFEST = FIG_DIR / "manifest.json"


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _bootstrap_rate(values: np.ndarray, n: int = 500, seed: int = 0) -> tuple[float, float, float]:
    if values.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(n, values.size), replace=True)
    rates = samples.mean(axis=1) * 100
    return float(np.median(rates)), float(np.percentile(rates, 2.5)), float(np.percentile(rates, 97.5))


def _render(snapshot_id: str = "v1") -> dict[str, Path]:
    labels_path = SETTINGS.paths.data_processed / f"labels_{snapshot_id}.parquet"
    df = pd.read_parquet(labels_path)
    if "hours_from_dst_min" not in df.columns:
        raise RuntimeError("labels parquet missing storm context")

    storm = df[df["storm_id"] > 0].copy()
    if storm.empty:
        raise RuntimeError("no storm-time windows")

    storm["bin"] = storm["hours_from_dst_min"].round().astype(int)
    edges = range(-48, 49)
    rate_med = []
    rate_lo = []
    rate_hi = []
    n_per_bin = []
    for h in edges:
        chunk = storm.loc[storm["bin"] == h, "label"].to_numpy()
        med, lo, hi = _bootstrap_rate(chunk)
        rate_med.append(med)
        rate_lo.append(lo)
        rate_hi.append(hi)
        n_per_bin.append(int(chunk.size))

    use("agu")
    fig, ax = plt.subplots(figsize=(7.2, 3.4))

    ax.fill_between(list(edges), rate_lo, rate_hi, color=COLORS["primary"], alpha=0.18, linewidth=0,
                    label="95% bootstrap CI")
    ax.plot(list(edges), rate_med, color=COLORS["primary"], linewidth=1.6, label="Median rate")
    ax.axvline(0, color=COLORS["warn"], linestyle="--", linewidth=0.8, label="Dst min")
    ax.set_xlabel("Hours from Dst minimum")
    ax.set_ylabel("EPB-positive rate [%]")
    ax.set_title("Superposed-epoch EPB rate around storm Dst min", loc="left")
    ax.legend(loc="upper right")

    # secondary axis: n samples per bin
    ax2 = ax.twinx()
    ax2.bar(
        list(edges),
        n_per_bin,
        width=0.85,
        color=COLORS["muted"],
        alpha=0.18,
        label="n windows",
    )
    ax2.set_ylabel("n windows per hour", color=COLORS["muted"])
    ax2.tick_params(axis="y", colors=COLORS["muted"])

    fig.tight_layout()

    out = {
        "pdf": FIG_DIR / "fig11_superposed_epoch.pdf",
        "png": FIG_DIR / "fig11_superposed_epoch.png",
    }
    for path in out.values():
        fig.savefig(path)
    plt.close(fig)
    return out


def _update_manifest(paths: dict[str, Path], snapshot_id: str) -> None:
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"figures": {}}
    manifest.setdefault("figures", {})["fig11_superposed_epoch"] = {
        "script": "paper/scripts/make_fig11_superposed_epoch.py",
        "snapshot_id": snapshot_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": {ext: str(p.relative_to(SETTINGS.paths.repo_root)) for ext, p in paths.items()},
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
