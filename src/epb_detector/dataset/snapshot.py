"""Persistable training-data snapshot.

Exports features, labels, and CV splits to ``data/training_snapshots/<id>/``
along with a ``meta.json`` manifest and a Hugging-Face-style dataset card.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from epb_detector.config import SETTINGS
from epb_detector.dataset.card import render_dataset_card
from epb_detector.models import splits


@dataclass(slots=True)
class SnapshotManifest:
    snapshot_id: str
    created_at: str
    git_sha: str
    rule_version: str
    n_windows: int
    n_positives: int
    n_station_days: int
    stations: list[str]
    years: list[int]
    feature_columns: list[str]
    sha256_features: str
    sha256_labels: str
    sha256_splits: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=SETTINGS.paths.repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_snapshot(
    labeled_features: pd.DataFrame,
    *,
    snapshot_id: str = "v0",
    feature_columns: list[str] | None = None,
) -> Path:
    """Persist a labeled feature frame to ``data/training_snapshots/<id>/``."""
    df = labeled_features.copy()
    if "label" not in df.columns:
        raise ValueError("labeled_features must include a 'label' column")
    out_dir = SETTINGS.paths.data_snapshots / snapshot_id
    out_dir.mkdir(parents=True, exist_ok=True)

    feat_cols = feature_columns or [
        c
        for c in df.columns
        if c not in {"label", "label_source", "rule_version", "rule_single_pos",
                     "rule_concurrent_sats"}
    ]

    # 1. features.parquet
    features_df = df[feat_cols].copy()
    features_df["window_id"] = np.arange(len(features_df), dtype="int64")
    feat_path = out_dir / "features.parquet"
    features_df.to_parquet(feat_path, index=False)

    # 2. labels.parquet
    label_cols = ["label", "label_source", "rule_version"]
    labels_df = df[label_cols].copy()
    labels_df["window_id"] = features_df["window_id"]
    labels_path = out_dir / "labels.parquet"
    labels_df.to_parquet(labels_path, index=False)

    # 3. splits.parquet — compute GroupKFold roles deterministically.
    folds = splits.group_kfold(df, n_splits=SETTINGS.train.n_splits)
    role = np.array(["train"] * len(df), dtype=object)
    if folds:
        _, val_idx = folds[0]
        role[val_idx] = "val"
    splits_df = pd.DataFrame(
        {
            "window_id": features_df["window_id"],
            "fold": 0,
            "role": role,
        }
    )
    splits_path = out_dir / "splits.parquet"
    splits_df.to_parquet(splits_path, index=False)

    # 4. meta.json
    rule_version = (
        df["rule_version"].iloc[0]
        if "rule_version" in df.columns and not df.empty
        else "unknown"
    )
    sta_doy_pairs = (
        df.groupby(["sta", df["window_start"].dt.date]).size().reset_index().shape[0]
        if "sta" in df.columns
        else 0
    )
    manifest = SnapshotManifest(
        snapshot_id=snapshot_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        git_sha=_git_sha(),
        rule_version=str(rule_version),
        n_windows=int(len(df)),
        n_positives=int((df["label"] == 1).sum()),
        n_station_days=sta_doy_pairs,
        stations=sorted(df["sta"].dropna().unique().tolist()) if "sta" in df else [],
        years=sorted(set(df["window_start"].dt.year.dropna().astype(int).tolist()))
        if "window_start" in df.columns
        else [],
        feature_columns=feat_cols,
        sha256_features=_sha256_file(feat_path),
        sha256_labels=_sha256_file(labels_path),
        sha256_splits=_sha256_file(splits_path),
    )
    with open(out_dir / "meta.json", "w") as f:
        json.dump(manifest.to_dict(), f, indent=2, sort_keys=True)

    # 5. dataset_card.md
    (out_dir / "dataset_card.md").write_text(render_dataset_card(manifest, df))

    return out_dir


def load_snapshot(snapshot_id: str = "v0") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Load (features, labels, splits, meta) for a snapshot."""
    snap_dir = SETTINGS.paths.data_snapshots / snapshot_id
    features = pd.read_parquet(snap_dir / "features.parquet")
    labels = pd.read_parquet(snap_dir / "labels.parquet")
    splits_df = pd.read_parquet(snap_dir / "splits.parquet")
    with open(snap_dir / "meta.json") as f:
        meta = json.load(f)
    return features, labels, splits_df, meta
