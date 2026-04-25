"""Classification metrics tailored to EPB detection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    roc_auc_score,
    roc_curve,
)


@dataclass(slots=True)
class ClassificationMetrics:
    pr_auc: float
    roc_auc: float
    brier: float
    f1_at_05: float
    far_at_tpr_90: float | None
    confusion: np.ndarray  # 2×2: [[TN, FP], [FN, TP]]
    n: int
    n_positive: int

    def to_dict(self) -> dict[str, float | int | list[list[int]]]:
        return {
            "pr_auc": float(self.pr_auc),
            "roc_auc": float(self.roc_auc),
            "brier": float(self.brier),
            "f1_at_05": float(self.f1_at_05),
            "far_at_tpr_90": float(self.far_at_tpr_90) if self.far_at_tpr_90 is not None else None,
            "confusion": self.confusion.astype(int).tolist(),
            "n": int(self.n),
            "n_positive": int(self.n_positive),
        }


def evaluate(y_true: np.ndarray, y_score: np.ndarray) -> ClassificationMetrics:
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score).astype(float)
    n_pos = int((y_true == 1).sum())
    if n_pos == 0 or n_pos == len(y_true):
        # Degenerate; fill with NaN where the metric is undefined.
        nan = float("nan")
        cm = confusion_matrix(y_true, (y_score >= 0.5).astype(int), labels=[0, 1])
        return ClassificationMetrics(nan, nan, brier_score_loss(y_true, np.clip(y_score, 0, 1)),
                                     nan, None, cm, len(y_true), n_pos)
    pr_auc = float(average_precision_score(y_true, y_score))
    roc_auc = float(roc_auc_score(y_true, y_score))
    brier = float(brier_score_loss(y_true, np.clip(y_score, 0, 1)))
    y_pred = (y_score >= 0.5).astype(int)
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    fpr, tpr, _ = roc_curve(y_true, y_score)
    far_at_tpr_90: float | None
    if (tpr >= 0.9).any():
        far_at_tpr_90 = float(fpr[np.searchsorted(tpr, 0.9)])
    else:
        far_at_tpr_90 = None

    return ClassificationMetrics(
        pr_auc=pr_auc,
        roc_auc=roc_auc,
        brier=brier,
        f1_at_05=f1,
        far_at_tpr_90=far_at_tpr_90,
        confusion=cm,
        n=len(y_true),
        n_positive=n_pos,
    )
