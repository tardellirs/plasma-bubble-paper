"""Tests for cross-validation splits and metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from epb_detector.models import metrics, splits


def _frame(n_groups: int, rows_per_group: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for g in range(n_groups):
        sta = "ABCD"[g % 4]
        for _ in range(rows_per_group):
            rows.append(
                {
                    "sta": sta,
                    "year": 2023,
                    "doy": g + 1,
                    "x": rng.normal(),
                    "label": int(rng.random() > 0.5),
                }
            )
    return pd.DataFrame(rows)


def test_group_kfold_no_leakage() -> None:
    df = _frame(n_groups=10)
    groups = splits.station_day_groups(df)
    folds = splits.group_kfold(df, n_splits=5)
    assert len(folds) == 5
    for tr, va in folds:
        splits.assert_no_leakage(tr, va, groups)


def test_group_kfold_handles_few_groups() -> None:
    df = _frame(n_groups=2)  # fewer groups than requested splits
    folds = splits.group_kfold(df, n_splits=5)
    assert 2 <= len(folds) <= 5


def test_assert_no_leakage_raises_on_overlap() -> None:
    groups = np.array([0, 0, 1, 1, 2, 2])
    train_idx = np.array([0, 1, 2])
    val_idx = np.array([3, 4])  # group 1 appears in both
    with pytest.raises(AssertionError):
        splits.assert_no_leakage(train_idx, val_idx, groups)


def test_metrics_perfect_classifier() -> None:
    y = np.array([0, 0, 1, 1])
    m = metrics.evaluate(y, np.array([0.1, 0.2, 0.8, 0.9]))
    assert m.pr_auc == pytest.approx(1.0)
    assert m.roc_auc == pytest.approx(1.0)
    assert m.f1_at_05 == pytest.approx(1.0)
    assert m.confusion.tolist() == [[2, 0], [0, 2]]


def test_metrics_random_classifier() -> None:
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, size=2000)
    s = rng.random(size=2000)
    m = metrics.evaluate(y, s)
    # Random scores should give PR-AUC ≈ class prior; both AUCs near 0.5.
    assert 0.35 < m.pr_auc < 0.65
    assert 0.4 < m.roc_auc < 0.6
