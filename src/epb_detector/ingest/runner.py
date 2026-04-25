"""Run the pyOASIS pipeline for a single (station, year, doy).

Forces ``MPLBACKEND=Agg`` and ``show_plot=False`` so the run is headless.
Outputs land under ``OUTPUT/RINEX/<year>/<doy>/<sta>/`` per the existing
convention; we don't change that.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

from epb_detector.config import SETTINGS


def _ensure_output_dirs(year: int, doy: int, sta: str) -> tuple[Path, Path]:
    sta_out = (
        SETTINGS.paths.pyoasis_output
        / "RINEX"
        / f"{year}"
        / f"{doy:03d}"
        / sta
    )
    orbit_out = (
        SETTINGS.paths.pyoasis_output / "ORBITS" / f"{year}" / f"{doy:03d}"
    )
    sta_out.mkdir(parents=True, exist_ok=True)
    orbit_out.mkdir(parents=True, exist_ok=True)
    return sta_out, orbit_out


def run_pyoasis_pipeline(sta: str, year: int, doy: int) -> dict[str, Path]:
    """Execute SP3intp → RNXclean → RNXlevelling → ROTI/DTEC/SIDX/TEC for one day.

    Steps reuse the inputs already in ``INPUT/RINEX`` and ``INPUT/ORBITS`` —
    callers should fetch with :mod:`epb_detector.ingest.downloader` first.
    """
    import pyOASIS  # delayed import; matplotlib backend already pinned above

    sta_out, orbit_out = _ensure_output_dirs(year, doy, sta)

    rinex_dir = SETTINGS.paths.rinex_input
    orbit_in = SETTINGS.paths.orbit_input

    pyOASIS.SP3intp(str(year), f"{doy:03d}", orbit_in, orbit_out)
    pyOASIS.RNXclean(sta, f"{doy:03d}", str(year), rinex_dir, orbit_out, sta_out)
    pyOASIS.RNXlevelling(sta, sta_out, show_plot=False)
    pyOASIS.ROTIcalc(sta, f"{doy:03d}", str(year), sta_out, sta_out, show_plot=False)
    pyOASIS.DTECcalc(sta, f"{doy:03d}", str(year), sta_out, sta_out, show_plot=False)
    pyOASIS.SIDXcalc(sta, f"{doy:03d}", str(year), sta_out, sta_out, show_plot=False)
    try:
        pyOASIS.TECcalc(sta, f"{doy:03d}", str(year), sta_out, sta_out, show_plot=False)
    except Exception as e:
        # TECcalc requires a calibration solver that occasionally fails on
        # data-poor days; we record the failure but continue.
        (sta_out / "TECcalc.error.txt").write_text(repr(e))

    return {"station_dir": sta_out, "orbit_dir": orbit_out}
