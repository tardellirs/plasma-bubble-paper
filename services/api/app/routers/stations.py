"""Station catalog endpoints."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from epb_detector.catalog.stations import StationMeta, all_stations, get_station

router = APIRouter(prefix="/stations", tags=["stations"])


def _to_dict(s: StationMeta) -> dict:
    return asdict(s)


@router.get("")
def list_stations() -> list[dict]:
    return [_to_dict(s) for s in all_stations()]


@router.get("/{station_id}")
def fetch_station(station_id: str) -> dict:
    try:
        return _to_dict(get_station(station_id))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
