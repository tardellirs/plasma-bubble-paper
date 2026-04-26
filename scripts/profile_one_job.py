"""Profile a single station-day pyOASIS pipeline run.

Usage: python scripts/profile_one_job.py [STA] [YEAR] [DOY]
Defaults to BOAV 2024 002 (data already on disk).

Outputs per-stage perf_counter timings and a cProfile pstats dump
to scripts/profile.out — view with `python -m pstats scripts/profile.out`.
"""

from __future__ import annotations

import cProfile
import os
import pstats
import shutil
import sys
import time
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import pyOASIS  # noqa: E402

STA = sys.argv[1] if len(sys.argv) > 1 else "BOAV"
YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
DOY = int(sys.argv[3]) if len(sys.argv) > 3 else 2

INPUT_RINEX = REPO / "INPUT" / "RINEX"
INPUT_ORBITS = REPO / "INPUT" / "ORBITS"
OUT_BASE = REPO / "OUTPUT" / "PROFILE_RUN"
sta_out = OUT_BASE / "RINEX" / str(YEAR) / f"{DOY:03d}" / STA
orbit_out = OUT_BASE / "ORBITS" / str(YEAR) / f"{DOY:03d}"

# Wipe so we measure cold from RNXclean down (orbit interp is small)
if OUT_BASE.exists():
    shutil.rmtree(OUT_BASE)
sta_out.mkdir(parents=True)
orbit_out.mkdir(parents=True)


def _t(label: str, fn, *args, **kw):
    t0 = time.perf_counter()
    fn(*args, **kw)
    dt = time.perf_counter() - t0
    print(f"[STAGE] {label}: {dt:6.1f}s")
    return dt


def run() -> dict[str, float]:
    timings: dict[str, float] = {}
    timings["SP3intp"] = _t(
        "SP3intp",
        pyOASIS.SP3intp,
        str(YEAR),
        f"{DOY:03d}",
        str(INPUT_ORBITS),
        str(orbit_out),
    )
    timings["RNXclean"] = _t(
        "RNXclean",
        pyOASIS.RNXclean,
        STA,
        f"{DOY:03d}",
        str(YEAR),
        str(INPUT_RINEX),
        str(orbit_out),
        str(sta_out),
    )
    timings["RNXlevelling"] = _t(
        "RNXlevelling",
        pyOASIS.RNXlevelling,
        STA,
        str(sta_out),
        show_plot=False,
    )
    for name in ("ROTIcalc", "DTECcalc", "SIDXcalc"):
        fn = getattr(pyOASIS, name)
        timings[name] = _t(
            name, fn, STA, f"{DOY:03d}", str(YEAR), str(sta_out), str(sta_out), show_plot=False,
        )
    return timings


if __name__ == "__main__":
    profile_path = REPO / "scripts" / "profile.out"
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    timings = run()
    pr.disable()
    total = time.perf_counter() - t0
    pr.dump_stats(str(profile_path))

    print()
    print(f"=== TOTAL: {total:.1f}s ({total/60:.1f} min) ===")
    for k, v in timings.items():
        pct = 100 * v / total
        print(f"  {k:14s} {v:6.1f}s  {pct:5.1f}%")

    print()
    print("=== Top-25 functions by cumulative time ===")
    p = pstats.Stats(str(profile_path)).sort_stats("cumulative")
    p.print_stats(25)
