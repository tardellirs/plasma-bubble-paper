"""Multi-source labels (weak-v1 + literature-v1).

Produces a confidence-graded label per window:

    final_label = max(weak_v1, literature_v1)

    confidence = 1.0  if both sources mark positive
               = 0.7  if literature marks positive (case publicado)
               = 0.5  if only weak-v1 fires
               = 0.0  if neither
"""

from __future__ import annotations

import pandas as pd

from epb_detector.external.case_studies import to_dataframe as cases_to_df
from epb_detector.labels import weak as weak_module


def label_features_v2(features: pd.DataFrame) -> pd.DataFrame:
    """Apply weak-v1 + literature-v1 labels to a feature frame.

    Adds these columns:
      - ``label_weak``: 0/1, the original heuristic.
      - ``label_literature``: 0/1, marks every window for a (sta, year, doy)
        listed in case_studies.yaml that falls within the night band.
      - ``label`` (final): logical OR of the two sources.
      - ``label_confidence``: 0.0 / 0.5 / 0.7 / 1.0 (see module docstring).
      - ``label_source``: one of ``none|weak|literature|weak+literature``.
      - ``rule_version``: ``v2``.
    """
    df = features.copy()
    weak = weak_module.label_features(df).labels
    df["label_weak"] = weak["label"].astype("int8")
    df["rule_concurrent_sats"] = weak["rule_concurrent_sats"]
    df["rule_single_pos"] = weak["rule_single_pos"]

    cases = cases_to_df()
    if cases.empty:
        df["label_literature"] = 0
    else:
        cases_keys = cases[["station", "year", "doy"]].copy()
        cases_keys.columns = ["sta", "year", "doy"]
        cases_keys["case"] = 1
        keys = df[["sta", "year", "doy"]].merge(cases_keys, on=["sta", "year", "doy"], how="left")
        # A window only inherits the literature label when it is in the night
        # band (matching the heuristic's regional plausibility filter).
        night = (df["local_time_mean"] >= 19) | (df["local_time_mean"] <= 6)
        df["label_literature"] = (keys["case"].fillna(0).astype("int8") * night.astype("int8"))

    df["label"] = (
        ((df["label_weak"] == 1) | (df["label_literature"] == 1)).astype("int8")
    )
    confidence = pd.Series(0.0, index=df.index, dtype="float32")
    confidence[(df["label_weak"] == 1) & (df["label_literature"] == 1)] = 1.0
    confidence[(df["label_weak"] == 0) & (df["label_literature"] == 1)] = 0.7
    confidence[(df["label_weak"] == 1) & (df["label_literature"] == 0)] = 0.5
    df["label_confidence"] = confidence

    source = pd.Series("none", index=df.index, dtype=object)
    source[(df["label_weak"] == 1) & (df["label_literature"] == 0)] = "weak"
    source[(df["label_weak"] == 0) & (df["label_literature"] == 1)] = "literature"
    source[(df["label_weak"] == 1) & (df["label_literature"] == 1)] = "weak+literature"
    df["label_source"] = source
    df["rule_version"] = "v2"
    return df
