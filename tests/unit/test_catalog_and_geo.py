"""Tests for the station catalog, day selector, and geo helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from epb_detector.catalog import day_selector, stations
from epb_detector.geo import coords, magnetic


def test_catalog_loads_and_has_mvp_three() -> None:
    mvp = stations.mvp_stations()
    ids = {s.id for s in mvp}
    assert ids == {"BOAV", "SALU", "POAL"}


def test_get_station_case_insensitive() -> None:
    s = stations.get_station("salu")
    assert s.id == "SALU"
    assert s.region == "eia-crest-south"


def test_unknown_station_raises() -> None:
    with pytest.raises(KeyError):
        stations.get_station("XXXX")


def test_mvp_days_count_and_year() -> None:
    days = day_selector.mvp_days()
    assert len(days) == 10
    assert all(d.year == 2023 for d in days)
    assert all(1 <= d.doy <= 366 for d in days)


def test_phase2a_preset_size() -> None:
    days = day_selector.phase2a_days()
    # ~70-80 days spanning Sep 2023 → May 2024.
    assert 60 <= len(days) <= 100
    years = {d.year for d in days}
    assert years == {2023, 2024}


def test_phase2a_stations_have_eight() -> None:
    sts = stations.phase2a_stations()
    assert len(sts) == 8
    ids = {s.id for s in sts}
    # Span equator → mid-lat
    assert "BOAV" in ids and "POAL" in ids


def test_mvp_day_resolves_to_known_date() -> None:
    march_eq = next(d for d in day_selector.mvp_days() if d.doy == 79)
    assert march_eq.date.isoformat() == "2023-03-20"


def test_mapfun_at_30deg() -> None:
    # pyOASIS's mapfun returns the projection factor M with vTEC = M · sTEC,
    # so M(30°) = cos(arcsin(Re/(Re+h) · cos(30°))) ≈ 0.5880.
    assert coords.slant_to_vertical_factor(30.0) == pytest.approx(0.5880, abs=1e-3)


def test_mapfun_at_zenith() -> None:
    assert coords.slant_to_vertical_factor(90.0) == pytest.approx(1.0, abs=1e-3)


def test_local_time_wraps_correctly() -> None:
    lt = coords.utc_to_local_time_hours(
        datetime(2023, 12, 22, 0, 0, tzinfo=timezone.utc), -45.0
    )
    # UT 00:00 at 45°W → ~21:00 LT.
    assert lt == pytest.approx(21.0, abs=0.1)


def test_qd_lat_at_geomagnetic_equator_is_small() -> None:
    # Boa Vista is near the magnetic equator → |QD-lat| should be < 15°.
    boav = stations.get_station("BOAV")
    qd_lat, _ = magnetic.qd_lat_lon(
        boav.geodetic_lat_deg, boav.geodetic_lon_deg, 0.0, datetime(2023, 1, 1)
    )
    assert abs(float(qd_lat[0])) < 15.0


def test_qd_lat_in_porto_alegre_is_negative_midlat() -> None:
    poal = stations.get_station("POAL")
    qd_lat, _ = magnetic.qd_lat_lon(
        poal.geodetic_lat_deg, poal.geodetic_lon_deg, 0.0, datetime(2023, 1, 1)
    )
    assert -40.0 < float(qd_lat[0]) < -10.0


def test_local_time_array() -> None:
    times = np.array(
        ["2023-12-22T03:00:00", "2023-12-22T15:30:00"], dtype="datetime64[ns]"
    )
    lt = coords.utc_to_local_time_hours(times, -45.0)
    assert lt[0] == pytest.approx(0.0, abs=0.1)
    assert lt[1] == pytest.approx(12.5, abs=0.1)
