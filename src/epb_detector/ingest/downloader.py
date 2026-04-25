"""Wrap the existing ``download_inputs.py`` script with retries and idempotency.

The legacy script lives at the repo root and already understands the IBGE RBMC
RINEX archive plus the GFZ MGEX SP3 archive (including the pre-2018 ``.Z``
fallback). We import it as a module so we don't pay the cost of subprocess
boot per download.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

from epb_detector.config import SETTINGS

_REPO_ROOT = SETTINGS.paths.repo_root


def _load_legacy() -> object:
    spec = importlib.util.spec_from_file_location(
        "_legacy_download_inputs", _REPO_ROOT / "download_inputs.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not locate download_inputs.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("_legacy_download_inputs", module)
    spec.loader.exec_module(module)
    return module


_LEGACY = _load_legacy()


def fetch_rinex(station: str, year: int, doy: int, retries: int = 3) -> Path:
    """Download a RINEX observation file for the given (sta, year, doy)."""
    out_dir = SETTINGS.paths.rinex_input
    out_dir.mkdir(parents=True, exist_ok=True)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return _LEGACY.fetch_rinex_ibge(station, year, doy, out_dir)  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001
            last_exc = e
            time.sleep(2 ** attempt)
    raise RuntimeError(
        f"RINEX download failed for {station} {year}/{doy:03d}: {last_exc}"
    )


def fetch_sp3(year: int, doy: int, retries: int = 3) -> Path:
    """Download an MGEX SP3 file for the given (year, doy)."""
    out_dir = SETTINGS.paths.orbit_input
    out_dir.mkdir(parents=True, exist_ok=True)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return _LEGACY.fetch_sp3(year, doy, out_dir)  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001
            last_exc = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"SP3 download failed for {year}/{doy:03d}: {last_exc}")
