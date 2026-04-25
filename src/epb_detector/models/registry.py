"""Round-trip a tiny model registry to ``models/registry.json``.

Why JSON: the registry is human-readable, fits in <100 lines for a paper, and
can be diffed in PRs. Heavy artifacts (XGBoost JSON model, calibration spline)
are written next to the registry under ``models/<model_id>/``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from epb_detector.config import SETTINGS

_REGISTRY_PATH = SETTINGS.paths.models / "registry.json"


@dataclass(slots=True)
class ModelEntry:
    model_id: str
    git_sha: str
    rule_version: str
    snapshot_id: str
    created_at: str
    train_window_start: str
    train_window_end: str
    metrics: dict = field(default_factory=dict)
    hyperparams: dict = field(default_factory=dict)
    feature_columns: list[str] = field(default_factory=list)
    notes: str = ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load() -> dict[str, ModelEntry]:
    if not _REGISTRY_PATH.exists() or _REGISTRY_PATH.stat().st_size == 0:
        return {}
    with open(_REGISTRY_PATH) as f:
        raw = json.load(f)
    return {k: ModelEntry(**v) for k, v in raw.items()}


def save(entries: dict[str, ModelEntry]) -> None:
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_REGISTRY_PATH, "w") as f:
        json.dump(
            {k: asdict(e) for k, e in entries.items()},
            f,
            indent=2,
            sort_keys=True,
        )


def upsert(entry: ModelEntry) -> None:
    entries = load()
    entries[entry.model_id] = entry
    save(entries)
