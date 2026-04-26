"""Run the pyOASIS pipeline for a single (station, year, doy).

Forces ``MPLBACKEND=Agg`` and ``show_plot=False`` so the run is headless.
Outputs land under ``OUTPUT/RINEX/<year>/<doy>/<sta>/`` per the existing
convention; we don't change that.

**Resume policy**: only stages whose output is a *single, atomically
written* file are skipped when that file already exists:

- ``SP3intp`` (one CSV per day, shared across all stations of that day)
- ``ROTIcalc`` / ``DTECcalc`` / ``SIDXcalc`` / ``TECcalc`` (one CSV each)

``RNXclean`` and ``RNXlevelling`` write multi-file outputs (one ``.RNX2``
or ``.RNX3`` per satellite); a partial state from a mid-pipeline crash
would silently feed bad data into the leveling step. We **always** re-run
those — the orchestrator's per-station-day skip via ``cache.manifest`` is
the right resume layer for them.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

from epb_detector.config import SETTINGS

logger = logging.getLogger(__name__)

# NOTE: An earlier optimisation attempt pre-filtered the input RINEX to
# GPS + GLONASS only via :mod:`epb_detector.ingest.rinex_filter`. Empirical
# benchmark on a real 2023 multi-constellation file showed georinex parse
# at 1.31× faster (saving ~0.6s per call), but pyOASIS.RNX_CLEAN already
# filters by ``sv.startswith('G' | 'R')`` *before* the per-satellite loop,
# so the actual job wall-clock (dominated by polynomial fits + screening
# per satellite) was unchanged. The net job-level speedup was ~0.02%, so
# we don't wire the filter in. The module is kept as a utility for any
# future use case that bypasses pyOASIS RNX_CLEAN entirely.


def _ensure_output_dirs(year: int, doy: int, sta: str) -> tuple[Path, Path]:
    sta_out = SETTINGS.paths.pyoasis_output / "RINEX" / f"{year}" / f"{doy:03d}" / sta
    orbit_out = SETTINGS.paths.pyoasis_output / "ORBITS" / f"{year}" / f"{doy:03d}"
    sta_out.mkdir(parents=True, exist_ok=True)
    orbit_out.mkdir(parents=True, exist_ok=True)
    return sta_out, orbit_out


# --------------------------------------------------------------------------
# Per-stage "is this stage already done?" probes
# --------------------------------------------------------------------------


def _orbit_table_path(orbit_out: Path, year: int, doy: int) -> Path:
    return orbit_out / f"ORBITS_{year}_{doy:03d}.SP3"


def _index_done(sta_out: Path, sta: str, year: int, doy: int, suffix: str) -> bool:
    """``suffix`` is one of 'ROTI', 'DTEC', 'SIDX'.

    pyOASIS writes ``<STA>_<DOY>_<YEAR>_G_<SUFFIX>.txt`` for GPS and the
    ``_R_`` variant for GLONASS. We treat the stage as "done" if either
    constellation file exists — that's how pyOASIS marks completion when
    one constellation was missing.
    """
    g = sta_out / f"{sta}_{doy:03d}_{year}_G_{suffix}.txt"
    r = sta_out / f"{sta}_{doy:03d}_{year}_R_{suffix}.txt"
    return g.exists() or r.exists()


def _tec_done(sta_out: Path, sta: str, year: int, doy: int) -> bool:
    return (sta_out / f"{sta}_{doy:03d}_{year}_L1L2.TEC").exists()


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def run_pyoasis_pipeline(sta: str, year: int, doy: int) -> dict[str, object]:
    """Execute the full pyOASIS pipeline for a single station-day.

    Returns a dict including which stages were *executed* vs *skipped* so
    the orchestrator can log per-stage timing later if it wants.
    """
    import pyOASIS  # delayed import; matplotlib backend already pinned above

    sta_out, orbit_out = _ensure_output_dirs(year, doy, sta)

    rinex_dir = SETTINGS.paths.rinex_input
    orbit_in = SETTINGS.paths.orbit_input

    skipped: list[str] = []
    executed: list[str] = []

    rnx_input_dir = rinex_dir

    # 1. Orbit interpolation — shared across all stations for the same day.
    if _orbit_table_path(orbit_out, year, doy).exists():
        skipped.append("SP3intp")
        logger.info("[skip] SP3intp (%s/%03d) — orbit table already on disk", year, doy)
    else:
        pyOASIS.SP3intp(str(year), f"{doy:03d}", orbit_in, orbit_out)
        executed.append("SP3intp")

    # 2. RNX cleaning + 3. arc-wise leveling — always run. These write a
    # file per satellite, and a mid-stage crash leaves the dir in a state
    # that's indistinguishable from "completed but with one missing sat",
    # so a naive skip would silently corrupt the downstream indices.
    pyOASIS.RNXclean(sta, f"{doy:03d}", str(year), rnx_input_dir, orbit_out, sta_out)
    executed.append("RNXclean")
    pyOASIS.RNXlevelling(sta, sta_out, show_plot=False)
    executed.append("RNXlevelling")

    # 4. Indices. Each is independent of the others.
    if _index_done(sta_out, sta, year, doy, "ROTI"):
        skipped.append("ROTIcalc")
    else:
        pyOASIS.ROTIcalc(sta, f"{doy:03d}", str(year), sta_out, sta_out, show_plot=False)
        executed.append("ROTIcalc")

    if _index_done(sta_out, sta, year, doy, "DTEC"):
        skipped.append("DTECcalc")
    else:
        pyOASIS.DTECcalc(sta, f"{doy:03d}", str(year), sta_out, sta_out, show_plot=False)
        executed.append("DTECcalc")

    if _index_done(sta_out, sta, year, doy, "SIDX"):
        skipped.append("SIDXcalc")
    else:
        pyOASIS.SIDXcalc(sta, f"{doy:03d}", str(year), sta_out, sta_out, show_plot=False)
        executed.append("SIDXcalc")

    # 5. Calibrated TEC. Tolerated to fail on data-poor days.
    if _tec_done(sta_out, sta, year, doy):
        skipped.append("TECcalc")
    else:
        try:
            pyOASIS.TECcalc(sta, f"{doy:03d}", str(year), sta_out, sta_out, show_plot=False)
            executed.append("TECcalc")
        except Exception as e:
            (sta_out / "TECcalc.error.txt").write_text(repr(e))
            executed.append("TECcalc(failed)")

    return {
        "station_dir": sta_out,
        "orbit_dir": orbit_out,
        "executed": executed,
        "skipped": skipped,
    }
