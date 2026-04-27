# Plasma Bubble Paper

End-to-end pipeline, ML model, and scientific website for detecting **Equatorial Plasma Bubbles (EPBs)** from Brazilian RBMC GNSS stations.

[![CI](https://github.com/tardellirs/plasma-bubble-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/tardellirs/plasma-bubble-paper/actions/workflows/ci.yml)
[![Web](https://github.com/tardellirs/plasma-bubble-paper/actions/workflows/web.yml/badge.svg)](https://github.com/tardellirs/plasma-bubble-paper/actions/workflows/web.yml)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC_BY--NC_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Live demo](https://img.shields.io/badge/live-plasma--bubble.ifsp.dev-success.svg)](https://plasma-bubble.ifsp.dev)

Built around the [pyOASIS](https://github.com/giorgiopicanco/OASIS) ionospheric processing toolbox (Picanço et al., 2025), this repo adds bulk ingest, weak-label heuristics, an XGBoost classifier with calibration and SHAP attribution, a FastAPI service, a public Next.js showcase, and a publication-figure pipeline.

> Live site: **<https://plasma-bubble.ifsp.dev>**

---

## Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Pipeline](#pipeline)
- [Project layout](#project-layout)
- [Quick start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [API](#api)
- [Web app](#web-app)
- [Testing](#testing)
- [Deployment](#deployment)
- [Reproducing paper figures](#reproducing-paper-figures)
- [Status](#status)
- [Citation](#citation)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Overview

Equatorial Plasma Bubbles (EPBs) are post-sunset depletions in the F-region ionosphere that scintillate trans-ionospheric radio links and degrade GNSS positioning over the magnetic equator. This project turns the Brazilian RBMC GNSS network into a continuous EPB detector:

1. **Ingest** — pulls daily RINEX from IBGE and MGEX SP3 orbits from GFZ/JAX, runs the pyOASIS pipeline (clean → leveling → ROTI / ΔTEC / SIDX / TEC) per station-day.
2. **Featurize** — converts per-satellite arcs into 10-minute sliding windows with ~40 statistical, spectral, and geometric features, joined with space-weather indices (Kp/ap/Dst/F10.7).
3. **Label** — applies the Pi (1997) and Cherniak (2014) weak-label heuristics and reconciles with literature case studies.
4. **Train** — XGBoost with `GroupKFold` by station-day, isotonic calibration, SHAP attribution, model registry.
5. **Serve** — FastAPI exposes events, storms, training snapshots, validation metrics, and live ingest status.
6. **Visualise** — Next.js 14 + MapLibre + Recharts at `plasma-bubble.ifsp.dev`.
7. **Publish** — idempotent matplotlib scripts produce publication-grade figures with SHA-pinned dataset snapshots.

## Features

- **Reproducibility** — every figure stamped with `{snapshot_sha, model_id, seed, generated_at}` in `paper/figures/manifest.json`.
- **Three-host compute architecture** — public VPS + sustained ARM ingest + on-demand AMD burst, sharing a single parquet manifest.
- **pyOASIS perf patches** — vectorised inner loop and atomic SP3 writes yield 2.4–3.9× speedup with byte-identical outputs.
- **Storm-aware v2 labels** — Dst/Kp phase tagging and superposed-epoch analysis endpoints.
- **Independent validation** — recall against published case studies, not only self-consistency with weak labels.
- **CI** — GitHub Actions matrix `py3.10 / 3.11 / 3.12` plus Node 20 web build and Playwright e2e.

## Architecture

```
┌────────────────────┐     ┌────────────────────┐
│ IBGE RINEX (RBMC)  │     │ MGEX SP3 (GFZ/JAX) │
└──────────┬─────────┘     └──────────┬─────────┘
           │                          │
           └────────────┬─────────────┘
                        ▼
        ┌──────────────────────────────────┐
        │ pyOASIS                          │
        │ RNXclean → leveling →            │
        │ ROTI / ΔTEC / SIDX / TEC         │
        └──────────────┬───────────────────┘
                       ▼
        ┌──────────────────────────────────┐
        │ epb_detector                     │
        │ features → labels → XGBoost      │
        │ → calibration + SHAP → events    │
        └──────────────┬───────────────────┘
                       ▼
        ┌──────────────────────────────────┐
        │ FastAPI  ←→  Next.js (MapLibre)  │
        └──────────────┬───────────────────┘
                       ▼
        ┌──────────────────────────────────┐
        │ paper/figures/*.{pdf,png,svg}    │
        └──────────────────────────────────┘
```

### Compute hosts

| Host | Role | Hardware | Notes |
|---|---|---|---|
| **Hostinger VPS** | Public web + API | KVM AMD, 4 vCPU, 16 GB | `epb-api` + `epb-web` behind Traefik (Let's Encrypt DNS-01 via Cloudflare) |
| **Oracle Ampere A1** | Sustained ARM ingest | 4 OCPU, 24 GB | `epb-detector:arm64-opt`, 4 parallel workers, disk-aware cleanup loop |
| **Hetzner CCX33** | Burst AMD ingest | 8 vCPU AMD EPYC, 32 GB | Spun up on demand (~$0.12/h), destroyed after the run |

A shared `data/cache/manifest.parquet` tracks done / failed / pending per station-day; rsync between hosts keeps state in sync, and the orchestrator's resume logic skips already-completed stages.

## Pipeline

The 7-step pyOASIS pipeline driven by `main.py`:

| Step | Entry point | Output |
|---|---|---|
| 1 | `pyOASIS.SP3intp` | tabulated orbits `ORBITS_YYYY_DOY.SP3` |
| 2 | `pyOASIS.RNXclean` | per-satellite `STAT_SAT_DOY_YYYY.RNX{1,2}` |
| 3 | `pyOASIS.RNXlevelling` | leveled `.RNX3` |
| 4 | `pyOASIS.ROTIcalc` | `<STA>_<DOY>_<YEAR>_{G,R}_ROTI.txt` + PNG |
| 5 | `pyOASIS.DTECcalc` | ΔTEC series + PNG |
| 6 | `pyOASIS.SIDXcalc` | SIDX series + PNG |
| 7 | `pyOASIS.TECcalc` | absolute TEC + PNG |

Steps 1–3 are sequential and produce the leveled `.RNX3` files that all index calculators consume; steps 4–7 are independent.

The `epb_detector` layer reads those outputs and produces:

```
data/processed/features_v2.parquet           # 1.68M rows × 23 features
data/processed/labels_v2.parquet             # storm-aware labels
data/processed/predictions_v2.parquet        # window probabilities
data/processed/events/events_v2.parquet      # merged contiguous-positive events
data/training_snapshots/v2/                  # train/val/test splits + dataset_card.md
data/models/xgb_v0.3.0/booster.json          # weights
data/models/registry.json                    # metrics, hyperparams, feature columns
data/case_study_validation_v2.json           # data-aware recall against literature
data/cache/manifest.parquet                  # which (sta, year, doy) are done/failed
```

Routers and scripts use a **latest-version glob** pattern, so adding a new `vN` is picked up automatically.

## Project layout

```
plasma-bubble-paper/
├── pyOASIS/              upstream RINEX → ROTI / ΔTEC / SIDX / TEC core (vendored)
├── src/epb_detector/     EPB detection layer
│   ├── catalog/          RBMC stations + day selector
│   ├── ingest/           downloader, runner, ProcessPoolExecutor orchestrator
│   ├── io/               readers, pandera schemas, parquet writers
│   ├── geo/              IPP geometry + AACGM quasi-dipole
│   ├── features/         10-min sliding windows
│   ├── labels/           Pi 1997 / Cherniak 2014 + manual reconciliation
│   ├── models/           GroupKFold, XGBoost, calibration, SHAP, registry
│   ├── inference/        event extraction (contiguous-window merge)
│   ├── external/         Kp/ap/Dst/F10.7 + case-study YAML
│   ├── dataset/          versioned snapshots
│   └── cli/              `epb` typer CLI
├── services/api/         FastAPI app
├── web/                  Next.js 14 + Tailwind + MapLibre + Recharts
├── paper/                figure scripts, generated figures, LaTeX tables
├── docker/               compose.yml for api + web + ingest
├── tests/                unit + property + integration + API + e2e
├── notebooks/            01_eda, 02_label_audit, 03_baseline, colab_ramp
└── docs/                 phase plans + Phase 2-A results report
```
