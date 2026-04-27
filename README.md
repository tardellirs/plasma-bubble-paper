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
