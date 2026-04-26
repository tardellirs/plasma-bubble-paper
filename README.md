# Plasma Bubble Paper

End-to-end pipeline + ML model + scientific website for detecting **Equatorial
Plasma Bubbles (EPBs)** from Brazilian RBMC GNSS stations. Built around the
[pyOASIS](https://github.com/giorgiopicanco/OASIS) ionospheric processing
toolbox (Picanço et al., 2025), this repo adds bulk ingest, weak-label
heuristics, an XGBoost classifier with calibration + SHAP, a FastAPI service,
a public Next.js showcase, and a publication-figure pipeline.

Live site: **<https://plasma-bubble.ifsp.dev>**

---

## What's in here

```
plasma-bubble-paper/
├── pyOASIS/              # upstream RINEX → ROTI / ΔTEC / SIDX / TEC core (vendored)
├── src/epb_detector/     # the EPB detection layer (this project)
│   ├── catalog/          # RBMC stations + day selector (equinox / solstice / Kp strata)
│   ├── ingest/           # downloader, runner, ProcessPoolExecutor orchestrator,
│   │                     # parquet manifest, RINEX 2.11 pre-filter
│   ├── io/               # readers, pandera schemas, parquet writers
│   ├── geo/              # IPP geometry + AACGM quasi-dipole coords
│   ├── features/         # 10-min sliding windows, statistics, spectral, geometric
│   ├── labels/           # weak (Pi 1997 / Cherniak 2014) + manual reconciliation
│   ├── models/           # GroupKFold splits, XGBoost, calibration, SHAP, registry
│   ├── inference/        # event extraction (contiguous-window merge, dedup)
│   ├── external/         # Kp/ap/F10.7 (GFZ), Dst (WDC Kyoto), case-study YAML
│   ├── dataset/          # versioned snapshots (features+labels+splits+card)
│   └── cli/              # `epb` typer CLI
├── services/api/         # FastAPI: /events, /storms/*, /training-data/*, /ingest/status
├── web/                  # Next.js 14 + Tailwind + MapLibre + Recharts + shadcn/ui
├── paper/                # idempotent figure scripts (matplotlib, AGU/IEEE/slides_dark)
│   ├── scripts/          # one script per figure/table, SHA-pinned manifest.json
│   ├── figures/          # generated PDFs (vector) + PNGs (600 dpi) + SVGs
│   └── tables/           # LaTeX booktabs tables
├── docker/               # api + web + ingest compose (Traefik, dokploy-network)
├── tests/                # unit + property (hypothesis) + integration + API + Playwright e2e
├── notebooks/            # 01_eda, 02_label_audit, 03_baseline, colab_ramp
└── docs/                 # phase plans (ramp, storms, external labels)
```

## Pipeline at a glance

```
RBMC RINEX (IBGE)  +  MGEX SP3 (GFZ/JAX)
        │
        ▼
pyOASIS (RNXclean → leveling → ROTI/ΔTEC/SIDX/TEC)        ← per-satellite arcs
        │
        ▼
features (10-min windows × ~40 features) ── space weather (Kp / ap / Dst / F10.7)
        │
        ├─► weak labels (Pi 1997 / Cherniak 2014)
        ├─► literature case-studies (independent label source)
        └─► XGBoost (GroupKFold by station-day) → isotonic calibration → SHAP
        │
        ▼
events parquet ──► FastAPI ──► Next.js (map, storms, dataset, methods)
        │
        ▼
paper/figures/*.{pdf,png,svg}  +  paper/tables/*.tex
```

## Quick start

```bash
# Python 3.10–3.12 (the runtime container uses 3.11)
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,api,paper]"

# Tiny MVP run (3 stations × 10 days, ~30 min on a laptop)
epb ingest mvp
epb run-all                  # features → labels → snapshot → train → figures

# Web (local dev)
cd web && pnpm install && pnpm dev   # http://localhost:3000
```

The `epb` CLI is the unified entry point — see `epb --help` for every
subcommand (`ingest`, `features`, `labels`, `train`, `predict`, `events`,
`dataset snapshot`, `paper figure`, `serve`, `run-all`).

## Compute architecture — three servers

The full Phase 2-A ramp (8 stations × ~77 days ≈ 600 station-days) is split
across three machines, each picked for what it's good at. None shares
secrets; each holds only what it needs.

| Server | Role | Hardware | Purpose |
|---|---|---|---|
| **Hostinger VPS** | Public web + API | KVM AMD, 4 vCPU, 16 GB RAM | `epb-api` + `epb-web` containers behind Traefik with Let's Encrypt (DNS-01 via Cloudflare). Read-only public site at `plasma-bubble.ifsp.dev`. |
| **Oracle Ampere A1** | Sustained ingest worker | ARM64 (Neoverse N1), 4 OCPU, 24 GB RAM | Long-running `epb ingest phase2a` with 4 parallel workers. ARM image `epb-detector:arm64-opt`. Disk-aware cleanup loop reaps RNX1+RNX2 intermediates once `*ROTI.txt` lands. |
| **Hetzner CCX33** | Burst ingest worker | Dedicated AMD EPYC, 8 vCPU, 32 GB RAM | Spun up on demand to crunch the remaining queue ~3× faster than Oracle, then destroyed. AMD64 image `epb-detector:amd64-opt`. Pay-per-hour (~$0.12/h). |

Same Docker image (built `arm64-opt` and `amd64-opt`) runs on every host.
A shared parquet **manifest** (`data/cache/manifest.parquet`) tracks done /
failed / pending per station-day; rsync between hosts keeps state in sync,
and the orchestrator's resume logic cheaply skips already-completed stages.

The image bakes in two pyOASIS optimizations found via cProfile:

1. **`pd.Series → np.ndarray` upfront** in `ROTI_CALC` and `SIDX_CALC` —
   the per-window inner loop calls `np.mean(series[mask])` ~5× per window
   × ~2880 windows × ~50 sats. Eliminating pandas indexing/mean overhead
   gave a **3.9× speedup** on SIDX and **2.4×** on ROTI (byte-identical
   outputs verified by diff).
2. **SP3 filename pre-filter + atomic temp-then-rename writes** in
   `SP3_INTERPOLATE` — avoids quadratic scan when the orbits dir grows, and
   prevents half-written orbit tables from confusing resume logic on a
   mid-job kill.

## Tests

```bash
pytest -q                                 # unit + property + integration + API
pnpm -C web test                          # vitest
pnpm -C web exec playwright test          # e2e (chromium): map, storms, dataset, methods, a11y
```

Coverage targets: 85% on `epb_detector/{io,features,labels}`, 70% elsewhere.
The integration test runs the full ingest → features → train → predict
pipeline on a tiny RNX3 fixture in <30 s and asserts a PR-AUC threshold.

CI: GitHub Actions matrix `py3.10/3.11/3.12` + Node 20 web build + Playwright.

## Reproducing paper figures

Each figure has a script in `paper/scripts/make_figXX_*.py` that:

1. Reads a SHA-pinned dataset snapshot (`paper/snapshots/`).
2. Applies the matplotlib theme (AGU / IEEE / `slides_dark`) from `_style.py`.
3. Writes `paper/figures/figXX_name.{pdf,png,svg}`.
4. Updates `paper/figures/manifest.json` with `{snapshot_sha, model_id, seed,
   generated_at}`.

```bash
python paper/scripts/make_all.py          # regenerates everything
pytest paper/scripts/tests/               # asserts shapes, presence, no NaNs
```

Slides + poster source live in `paper/conference/` (Marp + Inkscape).

## License

Same as upstream OASIS: **CC BY-NC 4.0** (non-commercial). See `LICENSE`.

## Citation

```bibtex
@article{picanco2025oasis,
  title   = {OASIS: Open-Access System for Ionospheric Studies},
  author  = {Picanço, G. and others},
  journal = {GPS Solutions},
  year    = {2025},
  note    = {submitted}
}
```

A `CITATION.cff` is provided for GitHub's citation widget.
