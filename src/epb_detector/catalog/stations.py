"""Station catalog loader.

Reads ``stations_rbmc.yaml`` and exposes ``StationMeta`` records with helpers
for filtering by region, MVP membership, and operating status. ECEF positions
are kept in meters (WGS84), matching the convention pyOASIS expects for the
receiver inputs to ``IonosphericPiercingPoint``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Literal

import yaml

Region = Literal["magnetic-equator", "eia-crest-south", "mid-latitude"]


@dataclass(frozen=True, slots=True)
class StationMeta:
    """Static metadata for one GNSS receiver station."""

    id: str
    name: str
    region: Region
    geodetic_lat_deg: float
    geodetic_lon_deg: float
    height_m: float
    ecef_x_m: float
    ecef_y_m: float
    ecef_z_m: float
    operator: str
    status: str
    mvp: bool


@cache
def _load_yaml() -> list[StationMeta]:
    raw = files("epb_detector.catalog").joinpath("stations_rbmc.yaml").read_text()
    payload = yaml.safe_load(raw)
    return [StationMeta(**entry) for entry in payload["stations"]]


def all_stations() -> list[StationMeta]:
    """Return all stations defined in the YAML catalog."""
    return list(_load_yaml())


def get_station(station_id: str) -> StationMeta:
    """Look up a station by its 4-letter code (case-insensitive)."""
    sid = station_id.upper()
    for s in _load_yaml():
        if s.id == sid:
            return s
    raise KeyError(f"Unknown station: {station_id!r}")


def mvp_stations() -> list[StationMeta]:
    """Stations flagged for the MVP run (Phase 1)."""
    return [s for s in _load_yaml() if s.mvp]


def phase2a_stations() -> list[StationMeta]:
    """Eight RBMC stations spanning equator → mid-latitude.

    Used by the Phase 2-A ramp (~480 station-days). Mid-latitude POAL/UFPR
    are kept as negative controls.
    """
    target = {"BOAV", "MAPA", "BELE", "SALU", "BRAZ", "PALM", "UFPR", "POAL"}
    return [s for s in _load_yaml() if s.id in target]


def stations_by_region(region: Region) -> list[StationMeta]:
    return [s for s in _load_yaml() if s.region == region]
