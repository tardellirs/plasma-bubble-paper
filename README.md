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

## Quick start

```bash
# Python 3.11 recommended; CI tests 3.10/3.11/3.12
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,api,paper]"

# Tiny MVP run: 3 stations × 10 days, ~30 min on a laptop
epb ingest mvp
epb run-all run-all          # nested group due to typer quirk

# Local web dev
cd web && pnpm install && pnpm dev          # http://localhost:3000
```

## Installation

### Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,api,paper]"
```

Optional extras:

- `dev` — pytest, ruff, mypy, hypothesis, pre-commit
- `api` — fastapi, uvicorn, httpx
- `paper` — matplotlib themes, seaborn

`pre-commit install` after the editable install enables the project's lint/format hooks (`.pre-commit-config.yaml`).

### Web

```bash
cd web
pnpm install
pnpm dev
```

### Docker

The runtime image bundles the pyOASIS perf patches and a pinned numpy/pandas:

```bash
docker buildx build --platform linux/arm64 -t epb-detector:arm64-opt -f Dockerfile --load .
docker buildx build --platform linux/amd64 -t epb-detector:amd64-opt -f Dockerfile --load .
```

Compose spec for production: `docker/compose.yml` (api + web + ingest worker, Traefik labels for `dokploy-network`).

## Usage

The unified entry point is the `epb` CLI (typer):

```bash
epb --help
epb ingest mvp                       # 3 stations × 10 days
epb ingest phase2a --skip BOAV       # Phase 2-A station list
epb features compute --version v2
epb labels compute --version v2
epb dataset snapshot --id v2
epb train --model-id xgb_v0.3.0 --snapshot v2
epb predict --model-id xgb_v0.3.0
epb events build --version v2
epb paper figure 10                  # regenerate fig10
epb serve                            # local FastAPI on :8000
epb run-all run-all                  # full pipeline (nested due to typer quirk)
```

Defaults match the production run (`v2` features, `v2` snapshot, `xgb_v0.3.0` model). Figure scripts fall back to the latest entry in `models/registry.json` when no `model_id` is passed.

## API

FastAPI routers live in `services/api/app/routers/`.

| Router | Notable endpoints |
|---|---|
| `events` | `GET /events`, `/events/summary`, `/events/timeseries?sta=&sat=&t0=&t1=`, `/events/day-roti?sta=&date=` |
| `storms` | `/storms/{timeline,catalog,by-phase,superposed-epoch}` (latest `labels_v*.parquet`) |
| `validation` | `/validation/case-studies` (latest `case_study_validation_v*.json`) |
| `dataset` | `/training-data/snapshots`, sample, distribution, download |
| `stations` | RBMC station catalogue with QD-lat |
| `ingest` | `/ingest/status` for live progress while a worker runs |
| `climatology` | LT × month × ROTI bins |

OpenAPI docs (Swagger UI) are served at `/api/docs` on the live deployment.

## Web app

Next.js 14 (app router) at `web/app/`:

| Route | Purpose |
|---|---|
| `/` | Landing — overview, latest run summary, key figures |
| `/map` | MapLibre + UTC slider, event markers, drawer with ROTI / ΔTEC / SIDX time-series |
| `/storms` | Storm catalogue, by-phase rates, superposed-epoch view |
| `/validation` | Recall against published case studies |
| `/dataset` | Snapshot browser, distribution, parquet download |
| `/methods` | Pipeline diagram, feature definitions, label heuristics |

The map slider snaps to UTC midnight (24h step); events are visible when their `[start, end]` overlaps `[cursor, cursor + 24h]`.

## Testing

```bash
pytest -q                                  # unit + property + integration + API
pnpm -C web test                           # vitest
pnpm -C web exec playwright test           # e2e (chromium): map, storms, dataset, methods, a11y
```

Coverage targets: 85% on `epb_detector/{io,features,labels}`, 70% elsewhere. The integration test runs the full ingest → features → train → predict pipeline on a tiny RNX3 fixture in <30 s and asserts a PR-AUC threshold.

CI matrix: GitHub Actions `py3.10 / 3.11 / 3.12` + Node 20 web build + Playwright.

## Deployment

Live patches without rebuilding the image:

**Python (API):**

```bash
scp services/api/app/routers/<file>.py root@<vps>:/tmp/
ssh root@<vps> 'docker cp /tmp/<file>.py epb-api:/app/services/api/app/routers/<file>.py
                docker restart epb-api'
```

**Frontend (web):** Next.js builds bundles ahead of time, so a full rebuild on the VPS is required:

```bash
ssh root@<vps> 'cd /opt/epb-detector && git pull && \
                cd docker && docker compose build web && \
                docker compose up -d --no-deps web'
```

**Burst ingest:** the recommended pattern for catching up the queue is a Hetzner CCX33 — build the AMD image locally, `docker save | gzip | scp`, rsync state from Oracle, run with `EPB_INGEST_WORKERS=8`, then rsync OUTPUT back and destroy the VM.

## Reproducing paper figures

Each figure has a script `paper/scripts/make_figXX_*.py` that:

1. Reads a SHA-pinned dataset snapshot.
2. Applies the matplotlib theme (AGU / IEEE / `slides_dark`) from `_style.py`.
3. Writes `paper/figures/figXX_name.{pdf,png,svg}`.
4. Updates `paper/figures/manifest.json` with `{snapshot_sha, model_id, seed, generated_at}`.

```bash
python paper/scripts/make_all.py        # regenerate everything
pytest paper/scripts/tests/             # asserts shapes, presence, no NaNs
```

Slides + poster source live in `paper/conference/` (Marp + Inkscape).

## Status

**Phase 2-A** is live — 8 RBMC stations × ~77 days (Sep 2023 – May 2024 = 539 station-days). 400 ingested OK, 181 failed (PALM/MAPA absent in the IBGE archive). Model `xgb_v0.3.0`, snapshot `v2`, 6,250 events served.

Headlines from [`docs/results-phase2a.md`](docs/results-phase2a.md):

- Test-fold PR-AUC = **0.9991** — but features and labels share inputs, so this is closer to "fidelity to the heuristic" than "true bubble recall".
- Independent recall against published case studies: **6/6 stations, 3/3 evaluable events**. This is the more meaningful number.
- Storm-phase rates came out `main (6.0%) > none (5.1%) > recovery (3.9%)`, the *opposite* of the Aarons (1991) canon. Either the phase-boundary definition has an issue, or it is a real result. Bootstrap CI per longitude/season is on the next-steps list.

The next thing that meaningfully moves the needle is **active learning** (a drawer where humans confirm/refute prob 0.4–0.7 events).

## Citation

If you use this work, please cite both pyOASIS and this repository.

```bibtex
@article{picanco2025oasis,
  title   = {OASIS: Open-Access System for Ionospheric Studies},
  author  = {Picanço, G. and others},
  journal = {GPS Solutions},
  year    = {2025},
  note    = {submitted}
}
```

A [`CITATION.cff`](CITATION.cff) is provided for GitHub's citation widget.

## License

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) (non-commercial), matching upstream OASIS. See [`LICENSE`](LICENSE).

## Acknowledgements

- **pyOASIS** — Picanço et al. ([github.com/giorgiopicanco/OASIS](https://github.com/giorgiopicanco/OASIS)).
- **RBMC** — Brazilian Continuous GNSS Network (IBGE).
- **MGEX** — Multi-GNSS Experiment SP3 orbits via GFZ and JAXA.
- **Space weather indices** — Kp/ap/F10.7 (GFZ Potsdam), Dst (WDC Kyoto).
