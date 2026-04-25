"""Resume / skip behaviour of the pyOASIS pipeline driver.

Verifies that ``run_pyoasis_pipeline`` no-ops each pyOASIS stage when its
expected output is already on disk. We mock pyOASIS itself so the test
runs in milliseconds and doesn't pull in the full RINEX / SP3 surface.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from epb_detector.ingest import runner


@pytest.fixture
def fake_pyoasis(monkeypatch):
    """Replace `pyOASIS` with a stub that records which entry points were called."""
    calls: list[str] = []

    def make(name: str):
        def fn(*args, **kwargs):
            calls.append(name)

        return fn

    stub = types.ModuleType("pyOASIS")
    for name in ("SP3intp", "RNXclean", "RNXlevelling", "ROTIcalc",
                 "DTECcalc", "SIDXcalc", "TECcalc"):
        setattr(stub, name, make(name))
    monkeypatch.setitem(sys.modules, "pyOASIS", stub)
    return calls


@pytest.fixture
def temp_layout(monkeypatch, tmp_path: Path):
    """Point SETTINGS at a fresh tmp tree so no real files get touched."""
    out = tmp_path / "OUTPUT"
    rinex_in = tmp_path / "INPUT" / "RINEX"
    orbit_in = tmp_path / "INPUT" / "ORBITS"
    out.mkdir(parents=True)
    rinex_in.mkdir(parents=True)
    orbit_in.mkdir(parents=True)
    monkeypatch.setattr(runner.SETTINGS.paths, "pyoasis_output", out)
    monkeypatch.setattr(runner.SETTINGS.paths, "rinex_input", rinex_in)
    monkeypatch.setattr(runner.SETTINGS.paths, "orbit_input", orbit_in)
    return out


def _seed_outputs(out: Path, sta: str, year: int, doy: int, *,
                  orbit: bool = False, rnx2: bool = False, rnx3: bool = False,
                  roti: bool = False, dtec: bool = False, sidx: bool = False,
                  tec: bool = False) -> None:
    """Plant the marker files that signal a stage as 'done' on disk."""
    sta_dir = out / "RINEX" / f"{year}" / f"{doy:03d}" / sta
    orbit_dir = out / "ORBITS" / f"{year}" / f"{doy:03d}"
    sta_dir.mkdir(parents=True, exist_ok=True)
    orbit_dir.mkdir(parents=True, exist_ok=True)
    if orbit:
        (orbit_dir / f"ORBITS_{year}_{doy:03d}.SP3").write_text("orbit table")
    if rnx2:
        (sta_dir / f"{sta}_G01_{doy:03d}_{year}.RNX2").write_text("rnx2")
    if rnx3:
        (sta_dir / f"{sta}_G01_{doy:03d}_{year}.RNX3").write_text("rnx3")
    if roti:
        (sta_dir / f"{sta}_{doy:03d}_{year}_G_ROTI.txt").write_text("roti")
    if dtec:
        (sta_dir / f"{sta}_{doy:03d}_{year}_G_DTEC.txt").write_text("dtec")
    if sidx:
        (sta_dir / f"{sta}_{doy:03d}_{year}_G_SIDX.txt").write_text("sidx")
    if tec:
        (sta_dir / f"{sta}_{doy:03d}_{year}_L1L2.TEC").write_text("tec")


def test_full_run_when_no_outputs(fake_pyoasis, temp_layout):
    """Cold start runs every stage."""
    result = runner.run_pyoasis_pipeline("SALU", 2023, 324)
    assert fake_pyoasis == [
        "SP3intp",
        "RNXclean",
        "RNXlevelling",
        "ROTIcalc",
        "DTECcalc",
        "SIDXcalc",
        "TECcalc",
    ]
    assert set(result["executed"]) == set(fake_pyoasis)
    assert result["skipped"] == []


def test_orbit_table_present_skips_sp3intp(fake_pyoasis, temp_layout):
    _seed_outputs(temp_layout, "SALU", 2023, 324, orbit=True)
    runner.run_pyoasis_pipeline("SALU", 2023, 324)
    assert "SP3intp" not in fake_pyoasis
    # Everything downstream still ran.
    assert "RNXclean" in fake_pyoasis and "RNXlevelling" in fake_pyoasis


def test_rnx_stages_never_skipped_with_partial_state(fake_pyoasis, temp_layout):
    """Even with partial RNX2/RNX3 files on disk, both RNX stages re-run.

    These stages write one file per satellite, so seeing *some* files there
    doesn't prove they're complete. A skip here would silently feed garbage
    into leveling. Resume happens at the orchestrator/manifest level.
    """
    _seed_outputs(temp_layout, "SALU", 2023, 324, orbit=True, rnx2=True, rnx3=True)
    result = runner.run_pyoasis_pipeline("SALU", 2023, 324)
    assert "SP3intp" not in fake_pyoasis      # atomic + shared → safe to skip
    assert "RNXclean" in fake_pyoasis         # always re-run
    assert "RNXlevelling" in fake_pyoasis
    assert "SP3intp" in result["skipped"]


def test_full_resume_skips_only_atomic_stages(fake_pyoasis, temp_layout):
    """All outputs present → skip the atomic ones, still re-run RNX stages."""
    _seed_outputs(temp_layout, "SALU", 2023, 324,
                  orbit=True, rnx2=True, rnx3=True,
                  roti=True, dtec=True, sidx=True, tec=True)
    runner.run_pyoasis_pipeline("SALU", 2023, 324)
    # Only RNXclean + RNXlevelling re-run; everything atomic gets skipped.
    assert fake_pyoasis == ["RNXclean", "RNXlevelling"]


def test_index_skipped_independently(fake_pyoasis, temp_layout):
    """Only DTEC missing → only DTECcalc runs among the index stages.

    RNXclean + RNXlevelling always run regardless of disk state.
    """
    _seed_outputs(temp_layout, "SALU", 2023, 324,
                  orbit=True, rnx2=True, rnx3=True,
                  roti=True, sidx=True, tec=True)
    runner.run_pyoasis_pipeline("SALU", 2023, 324)
    assert fake_pyoasis == ["RNXclean", "RNXlevelling", "DTECcalc"]


def test_glonass_only_index_counts_as_done(fake_pyoasis, temp_layout):
    """If only the GLONASS ROTI file is present, ROTIcalc is still skipped."""
    sta_dir = temp_layout / "RINEX" / "2023" / "324" / "SALU"
    sta_dir.mkdir(parents=True)
    (sta_dir / "SALU_324_2023_R_ROTI.txt").write_text("roti")
    # Seed everything else so we isolate the ROTI behaviour.
    _seed_outputs(temp_layout, "SALU", 2023, 324,
                  orbit=True, rnx2=True, rnx3=True,
                  dtec=True, sidx=True, tec=True)
    runner.run_pyoasis_pipeline("SALU", 2023, 324)
    assert "ROTIcalc" not in fake_pyoasis
