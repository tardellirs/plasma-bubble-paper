"""Pandera schemas for pyOASIS output and downstream feature tables."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

ROTI_SCHEMA = pa.DataFrameSchema(
    {
        "MJD": pa.Column(float, pa.Check.gt(40000), pa.Check.lt(80000)),
        "Longitude": pa.Column(float, pa.Check.in_range(0, 360)),
        "Latitude": pa.Column(float, pa.Check.in_range(-90, 90)),
        "Height": pa.Column(float, pa.Check.ge(0)),
        "Elevation": pa.Column(float, pa.Check.in_range(0, 90)),
        "ROTI": pa.Column(float, nullable=True),
        "STA": pa.Column(str),
        "SAT": pa.Column(str),
    },
    strict=False,
    coerce=True,
)

DTEC_SCHEMA = pa.DataFrameSchema(
    {
        "MJD": pa.Column(float, pa.Check.gt(40000)),
        "Longitude": pa.Column(float, pa.Check.in_range(0, 360)),
        "Latitude": pa.Column(float, pa.Check.in_range(-90, 90)),
        "Elevation": pa.Column(float, pa.Check.in_range(0, 90)),
        "DTEC": pa.Column(float, nullable=True),
        "STA": pa.Column(str),
        "SAT": pa.Column(str),
    },
    strict=False,
    coerce=True,
)

SIDX_SCHEMA = pa.DataFrameSchema(
    {
        "MJD": pa.Column(float, pa.Check.gt(40000)),
        "Longitude": pa.Column(float, pa.Check.in_range(0, 360)),
        "Latitude": pa.Column(float, pa.Check.in_range(-90, 90)),
        "Elevation": pa.Column(float, pa.Check.in_range(0, 90)),
        "SIDX": pa.Column(float, nullable=True),
        "STA": pa.Column(str),
        "SAT": pa.Column(str),
    },
    strict=False,
    coerce=True,
)


class FeatureRow(pa.DataFrameModel):
    """One row per (station, satellite, window_start). Used for ML features."""

    sta: Series[str]
    sat: Series[str]
    window_start: Series[pd.DatetimeTZDtype] = pa.Field(dtype_kwargs={"tz": "UTC"})
    window_end: Series[pd.DatetimeTZDtype] = pa.Field(dtype_kwargs={"tz": "UTC"})

    roti_max: Series[float] = pa.Field(nullable=True)
    roti_p95: Series[float] = pa.Field(nullable=True)
    roti_mean: Series[float] = pa.Field(nullable=True)
    roti_std: Series[float] = pa.Field(nullable=True)
    roti_duration_above: Series[float] = pa.Field(nullable=True, ge=0)
    roti_slope: Series[float] = pa.Field(nullable=True)

    elevation_mean: Series[float] = pa.Field(in_range={"min_value": 0, "max_value": 90})
    ipp_lon_mean: Series[float] = pa.Field(in_range={"min_value": -180, "max_value": 360})
    ipp_lat_mean: Series[float] = pa.Field(in_range={"min_value": -90, "max_value": 90})
    qd_lat_mean: Series[float] = pa.Field(nullable=True)
    local_time_mean: Series[float] = pa.Field(in_range={"min_value": 0, "max_value": 24})

    n_samples: Series[int] = pa.Field(ge=1)

    class Config:
        strict = False
        coerce = True
