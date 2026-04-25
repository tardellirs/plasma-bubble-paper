"""Geometric helpers around the IPP — wraps pyOASIS thin-shell utilities."""

from __future__ import annotations

from datetime import datetime

import numpy as np
from pyOASIS.settings import IonosphericPiercingPoint, mapfun

EARTH_RADIUS_KM = 6371.0
SHELL_HEIGHT_KM = 450.0


def slant_to_vertical_factor(elevation_deg: float | np.ndarray) -> np.ndarray:
    """Projection factor M(El) such that ``vTEC = M · sTEC``.

    Wraps :func:`pyOASIS.settings.mapfun`, which uses the thin-shell formula
    ``M = cos(arcsin(Re/(Re+h) · cos(El)))``. M is 1 at zenith and ~0.59 at
    El = 30° for a 450-km shell. Multiply sTEC by ``M`` to obtain vTEC.
    """
    return np.asarray(mapfun(np.asarray(elevation_deg)))


def utc_to_local_time_hours(
    utc: datetime | np.ndarray, longitude_deg: float | np.ndarray
) -> np.ndarray:
    """Approximate local solar time from UT and longitude (no equation-of-time)."""
    if isinstance(utc, datetime):
        utc_hours = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
    else:
        # numpy datetime64 → fractional hours of day
        ts = np.asarray(utc, dtype="datetime64[ns]")
        midnight = ts.astype("datetime64[D]")
        utc_hours = (ts - midnight) / np.timedelta64(1, "h")
    lt = np.asarray(utc_hours, dtype="float64") + np.asarray(longitude_deg) / 15.0
    return lt % 24.0


__all__ = [
    "EARTH_RADIUS_KM",
    "SHELL_HEIGHT_KM",
    "IonosphericPiercingPoint",
    "slant_to_vertical_factor",
    "utc_to_local_time_hours",
]
