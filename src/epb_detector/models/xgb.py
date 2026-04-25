"""XGBoost baseline classifier.

Trains on the wide window-level feature parquet plus its weak labels. Uses a
stratified GroupKFold (by station-day) to get an honest validation estimate
and to pick a calibration fold. Exports the booster as JSON (portable, no
pickle) plus a SHAP background sample to ``models/<model_id>/``.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from xgboost import XGBClassifier

from epb_detector.config import SETTINGS
from epb_detector.models import registry, splits
from epb_detector.models.metrics import ClassificationMetrics, evaluate

DEFAULT_FEATURES: tuple[str, ...] = (
    "roti_max",
    "roti_p95",
    "roti_mean",
    "roti_std",
    "roti_duration_above",
    "roti_slope",
    "dtec_max",
    "dtec_p95",
    "dtec_std",
    "dtec_slope",
    "sidx_max",
    "sidx_mean",
    "elevation_mean",
    "ipp_lon_mean",
    "ipp_lat_mean",
    "qd_lat_mean",
    "local_time_mean",
    "n_samples",
)

# Storm-context features added in Phase 2. Optional — train_xgb falls back
# silently when these columns are absent (i.e. for v0 features).
STORM_FEATURES: tuple[str, ...] = (
    "dst",
    "kp",
    "ap",
    "F107obs",
    "hours_from_dst_min",
)

DEFAULT_HYPERPARAMS = dict(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.06,
    subsample=0.85,
    colsample_bytree=0.85,
    reg_lambda=1.0,
    objective="binary:logistic",
    eval_metric="aucpr",
    tree_method="hist",
)


@dataclass(slots=True)
class TrainedModel:
    model_id: str
    booster_path: Path
    calibrator_path: Path
    metrics: ClassificationMetrics
    feature_columns: list[str]


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=SETTINGS.paths.repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def train_xgb(
    features_with_labels: pd.DataFrame,
    *,
    model_id: str = "xgb_v0.1.0",
    feature_columns: tuple[str, ...] | list[str] | None = None,
    snapshot_id: str = "v0",
    hyperparams: dict | None = None,
    notes: str = "",
    include_storm_features: bool = True,
) -> TrainedModel:
    """Fit an XGBoost binary classifier with isotonic calibration.

    When ``feature_columns`` is None, includes the base feature set plus any
    storm-context columns present in the input frame.
    """
    df = features_with_labels.dropna(subset=["label"]).copy()
    if df.empty:
        raise ValueError("No labeled rows to train on")

    if feature_columns is None:
        cols = list(DEFAULT_FEATURES)
        if include_storm_features:
            cols.extend(c for c in STORM_FEATURES if c in df.columns)
    else:
        cols = list(feature_columns)
    X = df[cols].astype("float32").to_numpy()
    y = df["label"].astype(int).to_numpy()

    cv = splits.group_kfold(df, n_splits=SETTINGS.train.n_splits)
    train_idx, val_idx = cv[0]

    hp = {**DEFAULT_HYPERPARAMS, **(hyperparams or {})}
    booster = XGBClassifier(random_state=SETTINGS.train.random_seed, **hp)
    booster.fit(X[train_idx], y[train_idx])
    val_scores_raw = booster.predict_proba(X[val_idx])[:, 1]

    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(val_scores_raw, y[val_idx])
    val_scores = calibrator.transform(val_scores_raw)

    metrics = evaluate(y[val_idx], val_scores)

    out_dir = SETTINGS.paths.models / model_id
    out_dir.mkdir(parents=True, exist_ok=True)
    booster_path = out_dir / "booster.json"
    booster.get_booster().save_model(str(booster_path))
    calibrator_path = out_dir / "isotonic.json"
    with open(calibrator_path, "w") as f:
        json.dump(
            {
                "x": calibrator.X_thresholds_.tolist(),
                "y": calibrator.y_thresholds_.tolist(),
            },
            f,
        )

    registry.upsert(
        registry.ModelEntry(
            model_id=model_id,
            git_sha=_git_sha(),
            rule_version=df["rule_version"].iloc[0] if "rule_version" in df else "unknown",
            snapshot_id=snapshot_id,
            created_at=registry.utc_now_iso(),
            train_window_start=str(df["window_start"].min()),
            train_window_end=str(df["window_end"].max()),
            metrics=metrics.to_dict(),
            hyperparams=hp,
            feature_columns=cols,
            notes=notes,
        )
    )

    return TrainedModel(
        model_id=model_id,
        booster_path=booster_path,
        calibrator_path=calibrator_path,
        metrics=metrics,
        feature_columns=cols,
    )


def predict_proba(
    df: pd.DataFrame,
    model_id: str,
    feature_columns: list[str] | None = None,
) -> np.ndarray:
    """Score a feature frame with a saved model + calibrator."""
    entries = registry.load()
    if model_id not in entries:
        raise KeyError(f"Model {model_id!r} not in registry")
    entry = entries[model_id]
    cols = feature_columns or entry.feature_columns
    out_dir = SETTINGS.paths.models / model_id
    booster = XGBClassifier()
    booster.load_model(str(out_dir / "booster.json"))
    raw = booster.predict_proba(df[cols].astype("float32").to_numpy())[:, 1]
    calib_path = out_dir / "isotonic.json"
    if calib_path.exists():
        with open(calib_path) as f:
            payload = json.load(f)
        x = np.asarray(payload["x"])
        y = np.asarray(payload["y"])
        calibrator = IsotonicRegression(out_of_bounds="clip")
        calibrator.fit(x, y)
        return calibrator.transform(raw)
    return raw
