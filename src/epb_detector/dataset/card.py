"""Render a Hugging-Face-style dataset card from a snapshot manifest."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from epb_detector.dataset.snapshot import SnapshotManifest


_TEMPLATE = """# EPB Detector Dataset Snapshot — {snapshot_id}

## Summary

- **Snapshot ID**: `{snapshot_id}`
- **Created at**: {created_at}
- **Git SHA**: `{git_sha}`
- **Rule version**: `{rule_version}`

## Composition

| Field | Value |
|-------|-------|
| Total windows | {n_windows:,} |
| Positive (EPB-labelled) windows | {n_positives:,} ({pct_pos:.2f}%) |
| Station-days covered | {n_station_days} |
| Stations | {stations} |
| Years | {years} |
| Number of features | {n_features} |

## Label distribution by station

{station_table}

## Label distribution by month

{month_table}

## Feature columns

{feature_list}

## Files

- `features.parquet` (sha256 `{sha256_features}`)
- `labels.parquet` (sha256 `{sha256_labels}`)
- `splits.parquet` (sha256 `{sha256_splits}`)
- `meta.json` — full manifest

## Labelling protocol (rule {rule_version})

Each 10-minute window per (station, satellite) is labelled positive when **all**
of the following hold:

1. Local solar time at the IPP is within the night band (configured 19h–06h).
2. ROTI sustained ≥ 0.5 TECU/min for at least 5 minutes.
3. At least 2 satellites trip rule (1) inside a ±10° IPP-longitude corridor.
4. The IPP is at quasi-dipole latitude `|QD-lat| ≤ 20°`.

Citations: Pi et al. (1997, GRL); Cherniak, Krankowski & Zakharenkova (2014,
Adv. Space Res.).

## Known limitations

- Labels are *weak*: derived from a heuristic on processed indices, not from
  manual inspection. Subsequent versions will incorporate manual audits via the
  web UI.
- The MVP snapshot covers only a small subset of station-days; trained models
  may not generalise outside the represented latitudinal/seasonal regimes.
- ROTI clipped at 10 TECU/min by pyOASIS; very strong scintillation events are
  saturated.

## License

Released under the same Creative Commons Attribution-NonCommercial 4.0 (CC
BY-NC 4.0) license as the parent OASIS toolbox.
"""


def _station_table(df: pd.DataFrame) -> str:
    if "sta" not in df.columns:
        return "_(no station column)_"
    grouped = (
        df.groupby("sta")["label"]
        .agg(["count", "sum"])
        .rename(columns={"count": "windows", "sum": "positives"})
    )
    grouped["pct"] = (grouped["positives"] / grouped["windows"] * 100).round(2)
    return grouped.to_markdown()


def _month_table(df: pd.DataFrame) -> str:
    if "window_start" not in df.columns:
        return "_(no window_start column)_"
    monthly = (
        df.assign(month=df["window_start"].dt.to_period("M"))
        .groupby("month")["label"]
        .agg(["count", "sum"])
        .rename(columns={"count": "windows", "sum": "positives"})
    )
    monthly["pct"] = (monthly["positives"] / monthly["windows"] * 100).round(2)
    return monthly.to_markdown()


def render_dataset_card(manifest: SnapshotManifest, df: pd.DataFrame) -> str:
    pct_pos = (manifest.n_positives / max(1, manifest.n_windows)) * 100.0
    return _TEMPLATE.format(
        snapshot_id=manifest.snapshot_id,
        created_at=manifest.created_at,
        git_sha=manifest.git_sha,
        rule_version=manifest.rule_version,
        n_windows=manifest.n_windows,
        n_positives=manifest.n_positives,
        pct_pos=pct_pos,
        n_station_days=manifest.n_station_days,
        stations=", ".join(manifest.stations) or "_(none)_",
        years=", ".join(map(str, manifest.years)) or "_(none)_",
        n_features=len(manifest.feature_columns),
        station_table=_station_table(df),
        month_table=_month_table(df),
        feature_list="\n".join(f"- `{c}`" for c in manifest.feature_columns),
        sha256_features=manifest.sha256_features,
        sha256_labels=manifest.sha256_labels,
        sha256_splits=manifest.sha256_splits,
    )
