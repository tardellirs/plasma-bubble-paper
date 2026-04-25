"""Sliding-window construction over per-arc time series.

A *window* is a contiguous, fixed-duration slice of a single (station, satellite)
arc — i.e. a portion of an observation track where the receiver has continuous
phase lock on the satellite. Windows from different arcs (or different sats)
never overlap.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from epb_detector.config import SETTINGS


@dataclass(slots=True)
class Window:
    """A single (sta, sat, t0..t1) slice with the underlying samples."""

    sta: str
    sat: str
    start: pd.Timestamp
    end: pd.Timestamp
    samples: pd.DataFrame  # rows from the source frame, time-sorted


def split_arcs(
    df: pd.DataFrame,
    *,
    time_col: str = "time",
    gap_seconds: float = 600.0,
) -> list[pd.DataFrame]:
    """Cut a per-satellite frame into arcs by detecting time gaps.

    Two consecutive samples spaced more than ``gap_seconds`` apart start a new
    arc. The default tolerates the 2.5-min ROTI/DTEC cadence and still cuts
    when a satellite re-emerges after >10 min below the elevation cutoff.
    """
    if df.empty:
        return []
    df = df.sort_values(time_col, kind="stable").reset_index(drop=True)
    deltas = df[time_col].diff().dt.total_seconds()
    breaks = np.flatnonzero((deltas > gap_seconds).to_numpy())
    if not breaks.size:
        return [df]
    boundaries = [0, *breaks.tolist(), len(df)]
    return [
        df.iloc[boundaries[i] : boundaries[i + 1]].reset_index(drop=True)
        for i in range(len(boundaries) - 1)
    ]


def make_windows(
    df: pd.DataFrame,
    *,
    sta: str,
    sat: str,
    window_minutes: float | None = None,
    stride_minutes: float | None = None,
    min_samples: int | None = None,
    time_col: str = "time",
) -> list[Window]:
    """Yield fixed-duration windows over each contiguous arc in ``df``.

    The window strides every ``stride_minutes`` minutes; only windows with at
    least ``min_samples`` rows are returned.
    """
    cfg = SETTINGS.features
    win_min = float(window_minutes if window_minutes is not None else cfg.window_minutes)
    stride_min = float(stride_minutes if stride_minutes is not None else cfg.stride_minutes)
    min_n = int(min_samples if min_samples is not None else cfg.min_window_samples)

    win_td = pd.Timedelta(minutes=win_min)
    stride_td = pd.Timedelta(minutes=stride_min)

    out: list[Window] = []
    for arc in split_arcs(df, time_col=time_col):
        if arc.empty:
            continue
        t_start: pd.Timestamp = arc[time_col].iloc[0]
        t_last: pd.Timestamp = arc[time_col].iloc[-1]
        cursor = t_start
        while cursor + win_td <= t_last + stride_td:
            t1 = cursor + win_td
            mask = (arc[time_col] >= cursor) & (arc[time_col] < t1)
            chunk = arc.loc[mask]
            if len(chunk) >= min_n:
                out.append(
                    Window(
                        sta=sta,
                        sat=sat,
                        start=cursor,
                        end=t1,
                        samples=chunk.reset_index(drop=True),
                    )
                )
            cursor = cursor + stride_td
    return out
