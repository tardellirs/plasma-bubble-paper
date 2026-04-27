# Storm-stratified EPB Analysis (storms-v3)

**Model:** `xgb_v0.3.0` · **Snapshot:** v3 ·
**Window:** 2014-01 → 2024-12 ·
**Generated:** 2026-04-27T12:47:59.606623+00:00

## Executive summary

- **Solar-cycle modulation is the dominant signal.** EPB-positive rate
  scales monotonically with F10.7 phase quartile across the 31 intense+
  storms in the v3 sample: 0.0077 → 0.0134 → 0.0220 → **0.0350** —
  a **4.5× increase from solar minimum to solar maximum quartile**.
  This is the *positive* finding of the storms-v3 work and is consistent
  with the classical EUV-driven F-region instability picture (Aarons
  1991; Abdu 2012).
- **Storm-vs-quiet amplification is null on this sample.** Storm rate
  0.043 vs quiet 0.051, ratio **0.84× (95% CI [0.49, 1.28])**. The
  quiet baseline at solar maximum is already saturated with EPBs, so
  there is no headroom for storms to "boost" the rate over the cycle-
  averaged baseline that Q1 measures. Stratifying by cycle phase first
  (Q6) and *then* asking the storm question is the correct next step.
- **PRE-window amplification is null.** Storms with Dst-min in the
  PRE window vs other LTs: Mann-Whitney one-sided *p* = 0.663.
  Dst-min LT is too coarse a proxy for whether the PRE actually fired
  on a given storm (n=7 in PRE bin caps the test power regardless).
- **Independent recall on literature events: 5/5 evaluable events,
  10/11 (station, event) pairs** — including a 2017-09-08 storm
  (solar max conditions never seen in the model's 8-month training).
  See [`data/case_study_validation_v3.json`](../data/case_study_validation_v3.json).
- The full analysis JSON used to produce this report:
  [`data/processed/analysis_v3.json`](../data/processed/analysis_v3.json) ·
  companion: [`docs/storms-v3-stats.json`](storms-v3-stats.json).

## Storm catalog

We detected **31 intense+ storms** in the 11-year window.

| Class | Count |
|---|---:|
| intense | 156 |
| severe | 28 |
| moderate | 9 |
| super | 2 |


![Solar-cycle context](../paper/figures/fig15_solar_cycle_strip.png)

The 11-yr SSN curve, storm dots (red dots = |Dst| ≥ 100 nT), and the
Phase 2-A coverage band on a single canvas. This is the same view the
web `/storms` page renders at the top.

## Q1 — Storm vs quiet rate

Per-storm EPB-positive rate vs per-(station, day) quiet baseline,
night-time windows only.

- Storm rate (mean across 31 storms):
  **0.0434**
- Quiet rate (mean across station-day groups):
  **0.0514**
- Ratio: 0.84× (95% CI [0.49, 1.28], n=31 storms / 1244 quiet groups)

![Storm vs quiet](../paper/figures/fig12_storm_vs_quiet_v3.png)

## Q2 — LT amplification near sunset

### 4-bin descriptive

| LT bin | _fmt_lt_bin stat |
|---|---|
| pre_sunset | mean=0.021 (95% CI [0.005, 0.041], n=7) |
| **PRE (17–22 LT)** | mean=0.031 (95% CI [0.014, 0.051], n=6) |
| post_midnight | mean=0.063 (95% CI [0.020, 0.113], n=10) |
| morning | mean=0.047 (95% CI [0.014, 0.084], n=8) |

### 2-bin Mann-Whitney test (PRE-adjacent > non-PRE)

- PRE_adjacent (pre_sunset + PRE): mean=0.026 (95% CI [0.014, 0.039], n=13)
- non_PRE (post_midnight + morning): mean=0.056 (95% CI [0.026, 0.090], n=18)
- Mann-Whitney U one-sided p = **0.663** (reject null at α=0.05?
  no)

![LT polar](../paper/figures/fig13_storm_lt_polar.png)

## Q3 — Intensity response

Spearman ρ between |Dst|-min and per-storm rate:
**0.20** (p = 0.186,
n = 47).

![Intensity curve](../paper/figures/fig14_intensity_curve.png)

## Q4 — Recovery duration effect

- Short recovery (≤24 h, n=2):
  rate = 0.000
- Long recovery (≥72 h, n=9):
  rate = 0.015
- Mann-Whitney p (two-sided) = 0.074

![Recovery duration](../paper/figures/fig16_recovery_duration.png)

## Q5 — Pre-storm baseline drift

- Quiet baseline rate: 0.0196
- Pre-storm window (last 12.0 h before main_start):
  nan
- Elevation factor (pre / quiet):
  **nan×**

![Precursor](../paper/figures/fig17_precursor.png)

## Q6 — Solar-cycle modulation

EPB rate by F10.7 phase quartile:

- Q1 (phase 0.30–0.42, n=8): rate = 0.0077
- Q2 (phase 0.46–0.61, n=8): rate = 0.0134
- Q3 (phase 0.65–0.81, n=7): rate = 0.0220
- Q4 (phase 0.84–1.14, n=8): rate = 0.0350

![Cycle modulation](../paper/figures/fig18_cycle_modulation.png)

## Q7 — Inter-station correlation lag

Cross-correlation of EPB-positive rate during intense-storm windows
between **SALU** and **BRAZ**:

- Peak lag: **0 min**
- Peak correlation: 0.78

![Station lag](../paper/figures/fig19_station_lag.png)

## Honest caveats

- Pi/Cherniak heuristic still drives the labels — the model output
  isn't an independent ground truth. The case-study validation
  (5/5 events recovered) is the meaningful generalization metric.
  Active learning is the next gap to close.
- The v3 ingest captured **31 intense+ storms with GNSS data**, not the
  full 186 detected in the 11-yr Dst record. The 4-bin LT stratification
  has only 6–10 storms per bin, which is why Q2 reads as null even
  though the *direction* (PRE-adjacent < non-PRE) is the opposite of
  the hypothesis. Treat Q2 as suggestive of *no effect at this sample
  size*, not as a refutation of the PRE hypothesis itself.
- Q5 (pre-storm baseline drift) returned NaN — the
  `hours_from_dst_min` column on labels v3 has gaps for some storms;
  the metric is reported but not interpretable on this snapshot.
- The pre-registered Phase 2-A finding (`main > recovery`) does NOT
  survive on v3 — null result reported honestly.
- Brazilian-sector LT bin is computed from a constant longitude offset
  (-45°). For storms whose Dst-min hits at a high-cadence Dst sample
  this is fine; near the boundary times (17 / 22 LT) a 1-h Dst grid
  may shift a storm into the wrong bin.
- Q6 (solar-cycle modulation) is the strongest signal but the dataset
  is dominated by 2024 cycle-25 max and lacks cycle-23 max coverage —
  a longer baseline would test whether the trend is monotonic across
  cycles or specific to the descending-cycle-24 / ascending-cycle-25
  geometry the v3 sample captured.

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
for f in fig12_storm_vs_quiet_v3 fig13_storm_lt_polar fig14_intensity_curve \
         fig15_solar_cycle_strip fig16_recovery_duration fig17_precursor \
         fig18_cycle_modulation fig19_station_lag; do
  python paper/scripts/make_$f.py
done
python paper/scripts/make_results_storms_v3.py    # rewrites this file
```

## Sensitivity check — locked vs retrained model

The plan calls for the **primary** result to use the Phase 2-A locked
booster (`xgb_v0.3.0`, trained on 8 months Sep 2023-May 2024) and a
**sensitivity** retrain on the full 11-yr v3 sample. Both runs agree on
the qualitative conclusions (Q1 ratio < 1.0, Q2 PRE p > 0.5).

| Metric | Locked v0.3.0 (primary) | Retrained on v3 (sensitivity) |
|---|---|---|
| Q1 storm rate | 0.043 | 0.040 |
| Q1 quiet rate | 0.051 | 0.049 |
| Q1 ratio | 0.84x | 0.80x |
| Q1 CI lo | 0.49 | 0.47 |
| Q1 CI hi | 1.28 | 1.19 |
| Q2 PRE-adjacent rate | 0.026 | 0.025 |
| Q2 non-PRE rate | 0.056 | 0.050 |
| Q2 Mann-Whitney p | 0.663 | 0.771 |

**Verdict:** the model retrained on v3 (4x the storm count of Phase
2-A) reaches the same qualitative conclusions as the locked Phase 2-A
model applied to v3 data. The null findings on Q1 and Q2 are not an
artefact of the model class — they are a property of the data.

