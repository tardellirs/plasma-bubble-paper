# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`pyOASIS` (Open-Access System for Ionospheric Studies) is a GNSS post-processing toolbox that ingests RINEX v2/v3 observation files plus MGEX SP3 precise orbits and derives ionospheric indices (ROTI, ΔTEC, SIDX, absolute TEC) from arc-wise geometry-free leveled carrier-phase combinations. It deliberately avoids relying on external DCB or VTEC products. Supports GPS and GLONASS at 15 s or 30 s sampling.

## Commands

Install dependencies (the package itself is published as `pyOASIS`, but the source here is what `main.py` imports):

```bash
pip install -r requirements.txt
# or, to install the local package in editable mode:
pip install -e .
```

Run the full example pipeline (BOAV, 2023 DOY 049 — files already in `INPUT/`):

```bash
python main.py
```

Fetch RINEX + SP3 for a different station/day before running `main.py`:

```bash
python download_inputs.py STATION YEAR DOY     # e.g. BOAV 2023 49
```

Decompressed `.SP3` goes to `INPUT/ORBITS/`; observation `.yyo` goes to `INPUT/RINEX/`. RINEX comes from IBGE RBMC (Brazilian stations only); SP3 falls back across `GBM0MGXRAP_` / `GFZ0MGXRAP_` / `JAX0MGXFIN_` prefixes depending on the GPS week.

There is no test suite, lint config, or build system beyond `setup.py`.

## Pipeline architecture

`main.py` drives a 7-step pipeline against directories `INPUT/{RINEX,ORBITS}` and `OUTPUT/{RINEX,ORBITS}/<year>/<doy>/<station>`. The first three steps are sequential and produce the leveled `.RNX3` files that all index calculators consume; steps 4–7 are independent and can run in any order.

| Step | Entry point | Module | Output |
|------|-------------|--------|--------|
| 1 | `pyOASIS.SP3intp` | `SP3_INTERPOLATE.py` | tabulated orbits `ORBITS_YYYY_DOY.SP3` |
| 2 | `pyOASIS.RNXclean` | `RNX_CLEAN.py` (uses `screening_settings.py`) | per-satellite `STAT_SAT_DOY_YYYY.RNX1` then `.RNX2` |
| 3 | `pyOASIS.RNXlevelling` | `RNX_LEVELLING.py` | leveled `.RNX3` |
| 4 | `pyOASIS.ROTIcalc` | `ROTI_CALC.py` | ROTI series + PNG |
| 5 | `pyOASIS.DTECcalc` | `DTEC_CALC.py` | ΔTEC series + PNG |
| 6 | `pyOASIS.SIDXcalc` | `SIDX_CALC.py` | SIDX series + PNG |
| 7 | `pyOASIS.TECcalc` | `TEC_CAL.py` | absolute TEC + PNG |

### EPB detector (Phase 2)

A second project — `epb_detector` — sits on top of pyOASIS in `src/epb_detector/`. It is a uv-style monorepo workspace that adds:

- `epb ingest phase2a` — bulk ingest 8 RBMC stations × ~77 days of Sep 2023 → May 2024 (≈ 616 station-days). Uses `download_inputs.py` + `pyOASIS` directly. Resumable via `cache/manifest.parquet`.
- `epb features build`, `epb labels v2`, `epb dataset snapshot`, `epb train xgb`, `epb run-all` — post-ingest pipeline.
- `epb_detector.external.{space_weather, storms, case_studies}` — Kp/ap/F10.7 from GFZ, Dst from WDC Kyoto, plus a curated YAML of published EPB case-study events used as an independent label source.
- `services/api/` — FastAPI exposing `/events`, `/storms/*`, `/training-data/*`, `/ingest/status`. DuckDB over parquet.
- `web/` — Next.js 14 + Tailwind + MapLibre + Recharts. Pages: `/`, `/map`, `/storms`, `/dataset`, `/methods`.
- `paper/scripts/` — idempotent figure scripts (matplotlib + AGU/IEEE/slides_dark presets) writing to `paper/figures/{pdf,png,svg}` with SHA-pinned manifest.
- `notebooks/colab_ramp.ipynb` — self-contained notebook for running a wider ramp on Colab with Drive output (no MCP needed).

**Plans**:
- `docs/plan-phase2-storms-and-external-labels.md` — current Phase 2 plan (executed).

**Common ops**:
- `epb ingest status` or `GET /ingest/status` — live progress while ingest runs.
- `EPB_INGEST_WORKERS=4 epb ingest phase2a` — bumps concurrency.
- `epb run-all --features-version v2 --snapshot-id v2 --model-id xgb_v0.3.0` — rebuild everything after ingest.

Cross-cutting modules under `pyOASIS/`:

- `settings.py` — Earth/ionosphere constants (`Re=6371`, `hm=450`), ECEF↔geodetic via `pyproj`, the `IonosphericPiercingPoint` class (single-layer thin-shell IPP geometry: position, elevation, azimuth, mapping factor), and a Fortran-style `cholesky_solve`.
- `gnss_freqs.py` / `linear_combinations.py` — GNSS frequencies and the geometry-free / Melbourne–Wübbena / iono-free combinations.
- `screening_settings.py` — outlier detection (residuals vs. polynomial fits, recursive-mean threshold), arc selection helpers, MW combination. Used heavily by `RNX_CLEAN.py`.
- `levelling_settings.py` — helpers specific to arc-wise leveling.
- `glonass_channels.dat` — GLONASS frequency channel assignments (shipped via `package_data` in `setup.py`).

## Conventions worth knowing before editing

- Public entry points are re-exported from `pyOASIS/__init__.py`. New pipeline steps should be wired there to keep `main.py`-style scripts working.
- Index/calc functions take `(station, doy, year, input_folder, destination_directory, show_plot=True)`. `show_plot=True` calls `plt.show()` (blocking) **after** writing the PNG — pass `show_plot=False` for headless/batch runs.
- Satellite ECEF coordinates from `SP3_INTERPOLATE` are in **kilometres**; receiver ECEF coordinates are in **metres**. `IonosphericPiercingPoint.__init__` converts the receiver to km internally — do not convert it again upstream.
- File naming is load-bearing across stages. Per-satellite files follow `STAT_SAT_DOY_YYYY.RNX{1,2,3}`; tabulated orbits follow `ORBITS_YYYY_DOY.SP3`. Renaming requires updating every consumer.
- Several internal identifiers and comments are in Portuguese (e.g. `estacao`, `diretorio_principal`); keep them stable when editing rather than translating ad hoc.
- License is CC BY-NC 4.0 (non-commercial).
