"""Test configuration and shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_OUTPUT = REPO_ROOT / "OUTPUT" / "RINEX" / "2015" / "359" / "SALU"


@pytest.fixture(scope="session")
def sample_station_dir() -> Path:
    """Directory with the SALU/2015-12-25 pyOASIS run produced earlier in this repo."""
    if not SAMPLE_OUTPUT.exists():
        pytest.skip(f"sample output not found at {SAMPLE_OUTPUT}")
    return SAMPLE_OUTPUT


@pytest.fixture(scope="session")
def sample_roti_path(sample_station_dir: Path) -> Path:
    return sample_station_dir / "SALU_359_2015_G_ROTI.txt"


@pytest.fixture(scope="session")
def sample_dtec_path(sample_station_dir: Path) -> Path:
    return sample_station_dir / "SALU_359_2015_G_DTEC.txt"


@pytest.fixture(scope="session")
def sample_sidx_path(sample_station_dir: Path) -> Path:
    return sample_station_dir / "SALU_359_2015_G_SIDX.txt"


@pytest.fixture(scope="session")
def sample_rnx3_path(sample_station_dir: Path) -> Path:
    return sample_station_dir / "SALU_G05_359_2015.RNX3"


@pytest.fixture(scope="session")
def sample_rnx3_merged_path(sample_station_dir: Path) -> Path:
    return sample_station_dir / "SALU_359_2015_RNX3_merged.txt"


@pytest.fixture(scope="session")
def sample_tec_path(sample_station_dir: Path) -> Path:
    return sample_station_dir / "SALU_359_2015_L1L2.TEC"


@pytest.fixture(scope="session")
def sample_dcb_path(sample_station_dir: Path) -> Path:
    return sample_station_dir / "SALU_359_2015_L1L2.DCB"
