"""SP3 interpolation should only open files whose name matches the target day.

Without this filter, ``pyOASIS.SP3intp`` parses every ``.SP3`` in the orbit
directory and discards the ones whose date doesn't match — quadratic blow-up
once the orbit dir accumulates ~80+ files.
"""

from __future__ import annotations

from pathlib import Path

from pyOASIS import SP3_INTERPOLATE


def _minimal_sp3(date_str: str) -> str:
    """A tiny SP3-v2 stub with one position record at midnight of ``date_str``.

    `date_str` is "YYYY MM DD". pyOASIS only cares about the `* YYYY MM DD ...`
    epoch line and the satellite position rows after it.
    """
    yyyy, mm, dd = date_str.split()
    return (
        f"#cP{yyyy} {int(mm):2d} {int(dd):2d}  0  0  0.00000000      96   u+U IGS14 FIT  TEST                    \n"
        f"## 2278 432000.00000000   300.00000000 60150 0.0000000000000\n"
        f"+    1   G01\n"
        f"++         0\n"
        f"%c M  cc GPS ccc cccc cccc cccc cccc ccccc ccccc ccccc ccccc\n"
        f"%c cc cc ccc ccc cccc cccc cccc cccc ccccc ccccc ccccc ccccc\n"
        f"%f  1.2500000  1.025000000  0.00000000000  0.000000000000000\n"
        f"%f  0.0000000  0.000000000  0.00000000000  0.000000000000000\n"
        f"%i    0    0    0    0      0      0      0      0         0\n"
        f"%i    0    0    0    0      0      0      0      0         0\n"
        f"/* COMMENT\n"
        f"/* COMMENT\n"
        f"/* COMMENT\n"
        f"/* COMMENT\n"
        f"*  {yyyy} {int(mm):2d} {int(dd):2d}  0  0  0.00000000\n"
        f"PG01    1234.567890   2345.678901   3456.789012     12.345678\n"
        f"EOF\n"
    )


def test_sp3intp_targets_only_matching_filename(tmp_path: Path):
    """Drop in 3 SP3 files but ask for one specific day → SP3intp opens just one."""
    in_dir = tmp_path / "ORBITS_IN"
    out_dir = tmp_path / "ORBITS_OUT"
    in_dir.mkdir()
    out_dir.mkdir()

    # year=2023, doy=324 → 2023-11-20.
    (in_dir / "GBM0MGXRAP_20233240000_01D_05M_ORB.SP3").write_text(
        _minimal_sp3("2023 11 20")
    )
    # Distractors that should NOT be opened — give them obviously wrong dates
    # so the test fails loudly if the filter regresses (date mismatch is the
    # original safety net).
    (in_dir / "GBM0MGXRAP_20232480000_01D_05M_ORB.SP3").write_text(
        _minimal_sp3("2023 09 05")
    )
    (in_dir / "GBM0MGXRAP_20240050000_01D_05M_ORB.SP3").write_text(
        _minimal_sp3("2024 01 05")
    )

    SP3_INTERPOLATE.SP3intp("2023", "324", str(in_dir), str(out_dir))

    out = out_dir / "ORBITS_2023_324.SP3"
    assert out.exists()
    body = out.read_text()
    # Only 2023-11-20 records survive; the 09-05 / 2024-01-05 distractors
    # never made it into the table because their files weren't opened.
    assert "20-11-2023" in body
    assert "05-09-2023" not in body
    assert "05-01-2024" not in body


def test_sp3intp_falls_back_when_no_filename_matches(tmp_path: Path):
    """If no filename embeds the target year+doy, fall back to scanning all
    files. pyOASIS still discards records by date afterwards, so this only
    matters for archives that use unconventional naming."""
    in_dir = tmp_path / "ORBITS_IN"
    out_dir = tmp_path / "ORBITS_OUT"
    in_dir.mkdir()
    out_dir.mkdir()

    # File whose *name* doesn't contain the expected `<year><doy>` token
    # but whose *content* is for the right day.
    (in_dir / "weird-name.SP3").write_text(_minimal_sp3("2023 11 20"))

    SP3_INTERPOLATE.SP3intp("2023", "324", str(in_dir), str(out_dir))

    out = out_dir / "ORBITS_2023_324.SP3"
    assert out.exists()
    assert "20-11-2023" in out.read_text()
