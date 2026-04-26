"""Render docs/results-storms-v3.md from analysis_v3.json.

Self-documenting: reads the analysis JSON + storm catalog + paper
figures manifest, fills in headline numbers and embeds figure PNGs as
relative-path Markdown links so the file is readable on GitHub
without rebuilding anything.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _storms_v3_io import ANALYSIS_PATH, CATALOG_PATH

from epb_detector.config import SETTINGS

REPO = SETTINGS.paths.repo_root
OUT_PATH = REPO / "docs" / "results-storms-v3.md"


def _fmt_ratio(r: dict) -> str:
    return (
        f"{r['ratio']:.2f}× "
        f"(95% CI [{r['ci_lo']:.2f}, {r['ci_hi']:.2f}], "
        f"n={r.get('n_storms', '?')} storms / {r.get('n_quiet_groups', '?')} quiet groups)"
    )


def _fmt_lt_bin(b: dict) -> str:
    return (
        f"mean={b['mean']:.3f} (95% CI [{b['ci_lo']:.3f}, {b['ci_hi']:.3f}], n={b['n']})"
    )


def main() -> None:
    if not ANALYSIS_PATH.exists():
        raise FileNotFoundError(
            f"Missing {ANALYSIS_PATH} — run `epb analysis storms-v3` first."
        )
    a = json.loads(ANALYSIS_PATH.read_text())
    cat = pd.read_parquet(CATALOG_PATH) if CATALOG_PATH.exists() else None

    q1 = a["Q1_storm_vs_quiet"]
    q2 = a["Q2_lt_amplification"]
    q3 = a.get("Q3_intensity_curve", {})
    q4 = a.get("Q4_recovery_duration", {})
    q5 = a.get("Q5_pre_storm_baseline", {})
    q6 = a.get("Q6_solar_cycle", {})
    q7 = a.get("Q7_inter_station_lag", {})

    pre_mean = q2["two_bin"]["PRE_adjacent"]["mean"]
    non_pre_mean = q2["two_bin"]["non_PRE"]["mean"]
    pre_factor = pre_mean / non_pre_mean if non_pre_mean > 0 else float("nan")
    p_pre = q2["two_bin_mannwhitney_test"]["p_one_sided_greater"]

    n_intense = q1.get("n_intense_storms", "?")
    model_id = a.get("model_id_predicted_with", "(unknown)")
    generated_at = datetime.now(timezone.utc).isoformat()

    storm_class_table = ""
    if cat is not None and "storm_class" in cat.columns:
        cls_counts = cat["storm_class"].value_counts().to_dict()
        rows = "\n".join(f"| {k} | {v} |" for k, v in cls_counts.items())
        storm_class_table = (
            "| Class | Count |\n|---|---:|\n" + rows + "\n"
        )

    md = f"""# Storm-stratified EPB Analysis (storms-v3)

**Model:** `{model_id}` · **Snapshot:** v3 ·
**Window:** 2014-01 → 2024-12 ·
**Generated:** {generated_at}

## Executive summary

- **EPB rate during intense (|Dst| ≥ 100 nT) storms vs quiet baseline:**
  {_fmt_ratio(q1["ratio_storm_to_quiet"])}.
- **Storms with Dst-min in the PRE window (17–22 LT, Brazilian sector)
  amplify the EPB rate by an additional {pre_factor:.2f}×** vs storms
  whose Dst-min lands at other LTs. One-sided Mann-Whitney
  *p* = {p_pre:.3f}.
- **Solar-cycle modulation:** see Q6 below.
- The full analysis JSON used to produce this report:
  [`data/processed/analysis_v3.json`](../data/processed/analysis_v3.json).

## Storm catalog

We detected **{n_intense} intense+ storms** in the 11-year window.

{storm_class_table}

![Solar-cycle context](../paper/figures/fig15_solar_cycle_strip.png)

The 11-yr SSN curve, storm dots (red dots = |Dst| ≥ 100 nT), and the
Phase 2-A coverage band on a single canvas. This is the same view the
web `/storms` page renders at the top.

## Q1 — Storm vs quiet rate

Per-storm EPB-positive rate vs per-(station, day) quiet baseline,
night-time windows only.

- Storm rate (mean across {q1.get('n_intense_storms', '?')} storms):
  **{q1['storm_rate_mean']:.4f}**
- Quiet rate (mean across station-day groups):
  **{q1['quiet_rate_mean']:.4f}**
- Ratio: {_fmt_ratio(q1["ratio_storm_to_quiet"])}

![Storm vs quiet](../paper/figures/fig12_storm_vs_quiet_v3.png)

## Q2 — LT amplification near sunset

### 4-bin descriptive

| LT bin | {_fmt_lt_bin.__name__} stat |
|---|---|
| pre_sunset | {_fmt_lt_bin(q2['four_bin'].get('pre_sunset', {'mean': 0, 'ci_lo': 0, 'ci_hi': 0, 'n': 0}))} |
| **PRE (17–22 LT)** | {_fmt_lt_bin(q2['four_bin'].get('PRE', {'mean': 0, 'ci_lo': 0, 'ci_hi': 0, 'n': 0}))} |
| post_midnight | {_fmt_lt_bin(q2['four_bin'].get('post_midnight', {'mean': 0, 'ci_lo': 0, 'ci_hi': 0, 'n': 0}))} |
| morning | {_fmt_lt_bin(q2['four_bin'].get('morning', {'mean': 0, 'ci_lo': 0, 'ci_hi': 0, 'n': 0}))} |

### 2-bin Mann-Whitney test (PRE-adjacent > non-PRE)

- PRE_adjacent (pre_sunset + PRE): {_fmt_lt_bin(q2['two_bin']['PRE_adjacent'])}
- non_PRE (post_midnight + morning): {_fmt_lt_bin(q2['two_bin']['non_PRE'])}
- Mann-Whitney U one-sided p = **{p_pre:.3f}** (reject null at α=0.05?
  {'**yes**' if p_pre < 0.05 else 'no'})

![LT polar](../paper/figures/fig13_storm_lt_polar.png)

## Q3 — Intensity response

Spearman ρ between |Dst|-min and per-storm rate:
**{q3.get('spearman_rho', float('nan')):.2f}** (p = {q3.get('spearman_p', float('nan')):.3f},
n = {q3.get('n_storms', '?')}).

![Intensity curve](../paper/figures/fig14_intensity_curve.png)

## Q4 — Recovery duration effect

- Short recovery (≤24 h, n={q4.get('n_short', '?')}):
  rate = {q4.get('short_rate_mean', float('nan')):.3f}
- Long recovery (≥72 h, n={q4.get('n_long', '?')}):
  rate = {q4.get('long_rate_mean', float('nan')):.3f}
- Mann-Whitney p (two-sided) = {q4.get('p_two_sided', float('nan')):.3f}

![Recovery duration](../paper/figures/fig16_recovery_duration.png)

## Q5 — Pre-storm baseline drift

- Quiet baseline rate: {q5.get('quiet_rate', float('nan')):.4f}
- Pre-storm window (last {q5.get('pre_hours', '?')} h before main_start):
  {q5.get('pre_rate', float('nan')):.4f}
- Elevation factor (pre / quiet):
  **{q5.get('elevation_ratio', float('nan')):.2f}×**

![Precursor](../paper/figures/fig17_precursor.png)

## Q6 — Solar-cycle modulation

EPB rate by F10.7 phase quartile:

{chr(10).join(f"- Q{int(r['quartile']) + 1} (phase {r['phase_lo']:.2f}–{r['phase_hi']:.2f}, n={r['n']}): rate = {r['rate_mean']:.4f}" for r in q6.get('by_quartile', []))}

![Cycle modulation](../paper/figures/fig18_cycle_modulation.png)

## Q7 — Inter-station correlation lag

Cross-correlation of EPB-positive rate during intense-storm windows
between **{q7.get('pair', ['?', '?'])[0]}** and **{q7.get('pair', ['?', '?'])[1]}**:

- Peak lag: **{q7.get('peak_lag_min', '?')} min**
- Peak correlation: {q7.get('peak_corr', float('nan')):.2f}

![Station lag](../paper/figures/fig19_station_lag.png)

## Honest caveats

- Pi/Cherniak heuristic still drives the labels — the model output
  isn't an independent ground truth. Active learning (Phase 4 of the
  original plan) is the next gap to close.
- 11-year window contains only {n_intense} intense+ storms. PRE-bin
  events are the most physics-relevant, but the smallest sub-sample;
  treat the LT-stratified result as suggestive until it's reproduced
  on a longer baseline (cycle 23 max).
- Brazilian-sector LT bin is computed from a constant longitude offset
  (-45°). For storms whose Dst-min hits at a high-cadence Dst sample
  this is fine; near the boundary times (17 / 22 LT) a 1-h Dst grid
  may shift a storm into the wrong bin.
- Solar-cycle phase confound is partly absorbed by the matched-quiet
  control day selection.

## Reproduce

```bash
# 1. Storm catalog
epb storms detect --start 2014-01-01 --end 2024-12-31 --threshold-nt -100

# 2. Day plan + bulk ingest (Hetzner CCX33 burst recommended)
EPB_INGEST_WORKERS=8 epb ingest storm-stratified

# 3. Predict + analyze
epb run-all run-all --features-version v3 --snapshot-id v3 --model-id xgb_v0.3.0
epb analysis storms-v3 --threshold 0.5 --n-boot 1000

# 4. Figures + this report
for f in fig12_storm_vs_quiet_v3 fig13_storm_lt_polar fig14_intensity_curve \\
         fig15_solar_cycle_strip fig16_recovery_duration fig17_precursor \\
         fig18_cycle_modulation fig19_station_lag; do
  python paper/scripts/make_$f.py
done
python paper/scripts/make_results_storms_v3.py    # rewrites this file
```
"""

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(md)
    print(f"Wrote {OUT_PATH} ({len(md):,} chars)")


if __name__ == "__main__":
    main()
