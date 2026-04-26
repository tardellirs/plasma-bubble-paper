"""Shared IO helpers for the storms-v3 figure scripts.

Centralises:
- locating ``analysis_v3.json``, ``predictions_v3.parquet``, ``storm_catalog_v3.parquet``;
- updating ``paper/figures/manifest.json`` with sha + timestamp;
- writing the (pdf, png, svg) triple for a figure.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from epb_detector.config import SETTINGS

FIG_DIR = SETTINGS.paths.paper_figures
MANIFEST = FIG_DIR / "manifest.json"
ANALYSIS_PATH = SETTINGS.paths.data_processed / "analysis_v3.json"
PREDICTIONS_PATH = SETTINGS.paths.data_processed / "predictions_v3.parquet"
CATALOG_PATH = SETTINGS.paths.data_processed / "storm_catalog_v3.parquet"


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_analysis() -> dict[str, Any]:
    if not ANALYSIS_PATH.exists():
        raise FileNotFoundError(
            f"Missing {ANALYSIS_PATH} — run `epb analysis storms-v3` first."
        )
    return json.loads(ANALYSIS_PATH.read_text())


def save_figure(fig, fig_id: str, *, snapshot_id: str = "v3", model_id: str = "xgb_v0.3.0", extra: dict[str, Any] | None = None) -> dict[str, Path]:
    """Write {pdf, png, svg} and update the manifest. Returns the paths."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {
        ext: FIG_DIR / f"{fig_id}.{ext}" for ext in ("pdf", "png", "svg")
    }
    for path in out.values():
        fig.savefig(path)

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"figures": {}}
    manifest.setdefault("figures", {})[fig_id] = {
        "script": f"paper/scripts/make_{fig_id}.py",
        "snapshot_id": snapshot_id,
        "model_id": model_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": {
            ext: str(p.relative_to(SETTINGS.paths.repo_root)) for ext, p in out.items()
        },
        "sha256": {ext: _file_sha256(p) for ext, p in out.items()},
        **(extra or {}),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return out
