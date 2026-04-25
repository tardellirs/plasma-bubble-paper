"""Cross-validation splits with leakage protection.

Split rows by (station, day-of-year) so that two windows from the same
station-day never appear in different folds. ``GroupKFold`` from scikit-learn
handles this once we encode the group key.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from epb_detector.config import SETTINGS


def station_day_groups(features: pd.DataFrame) -> np.ndarray:
    """Stable integer group label per (sta, year, doy) station-day."""
    if "year" in features.columns and "doy" in features.columns:
        keys = features[["sta", "year", "doy"]].astype(str).agg("-".join, axis=1)
    else:
        # fall back to derived year-month-day from window_start
        ts = pd.DatetimeIndex(features["window_start"])
        keys = (
            features["sta"].astype(str)
            + "-"
            + ts.year.astype(str)
            + "-"
            + ts.dayofyear.astype(str)
        )
    return pd.Categorical(keys).codes.astype("int64")


def group_kfold(features: pd.DataFrame, n_splits: int | None = None) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return a list of (train_idx, val_idx) tuples respecting station-day groups."""
    n = int(n_splits or SETTINGS.train.n_splits)
    groups = station_day_groups(features)
    n_unique = int(np.unique(groups).size)
    n_eff = max(2, min(n, n_unique))
    cv = GroupKFold(n_splits=n_eff)
    return [(tr, va) for tr, va in cv.split(features, groups=groups)]


def assert_no_leakage(train_idx: np.ndarray, val_idx: np.ndarray, groups: np.ndarray) -> None:
    """Raise if any group appears in both train and val splits."""
    overlap = set(groups[train_idx]) & set(groups[val_idx])
    if overlap:
        raise AssertionError(f"Station-day leakage between train/val: {sorted(overlap)[:5]}")
