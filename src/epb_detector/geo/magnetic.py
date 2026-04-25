"""Magnetic-coordinate conversions (Quasi-Dipole) via aacgmv2.

Falls back to a closed-form centered-dipole approximation if aacgmv2 is not
installed (Windows or sandboxed CI). The dipole approximation is accurate to
a few degrees in QD latitude for the equatorial and low-latitude regions we
care about.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

try:
    import aacgmv2

    _HAS_AACGMV2 = True
except ImportError:  # pragma: no cover
    _HAS_AACGMV2 = False

# IGRF 2020 centered-dipole pole (geographic coordinates).
_DIPOLE_POLE_LAT_DEG = 80.65
_DIPOLE_POLE_LON_DEG = -72.68


def _centered_dipole_qdlat(
    lat_deg: float | np.ndarray, lon_deg: float | np.ndarray
) -> np.ndarray:
    """Closed-form magnetic latitude using a centered-dipole approximation."""
    lat_r = np.deg2rad(lat_deg)
    lon_r = np.deg2rad(lon_deg)
    pole_lat_r = np.deg2rad(_DIPOLE_POLE_LAT_DEG)
    pole_lon_r = np.deg2rad(_DIPOLE_POLE_LON_DEG)
    sin_mlat = np.sin(lat_r) * np.sin(pole_lat_r) + np.cos(lat_r) * np.cos(pole_lat_r) * np.cos(
        lon_r - pole_lon_r
    )
    return np.rad2deg(np.arcsin(np.clip(sin_mlat, -1.0, 1.0)))


def qd_lat_lon(
    lat_deg: float | np.ndarray,
    lon_deg: float | np.ndarray,
    height_km: float | np.ndarray,
    when: datetime,
) -> tuple[np.ndarray, np.ndarray]:
    """Quasi-Dipole latitude/longitude at the given geodetic point and time."""
    lat_arr = np.atleast_1d(np.asarray(lat_deg, dtype="float64"))
    lon_arr = np.atleast_1d(np.asarray(lon_deg, dtype="float64"))
    h_arr = np.atleast_1d(np.asarray(height_km, dtype="float64"))
    if _HAS_AACGMV2:
        qd_lat, qd_lon, _ = aacgmv2.convert_latlon_arr(
            lat_arr,
            ((lon_arr + 180) % 360) - 180,  # aacgmv2 wants -180..180
            h_arr,
            when,
            method_code="G2A",
        )
        return np.asarray(qd_lat), np.asarray(qd_lon)
    qd_lat = _centered_dipole_qdlat(lat_arr, lon_arr)
    return qd_lat, lon_arr.copy()
