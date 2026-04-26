"""Pick (year, doy) pairs to ingest.

The MVP preset spans the equinoxes (March, September) and the December solstice
of a high-activity year (2023), interleaving geomagnetically active and quiet
days. The set is small and deterministic so it can be committed to fixtures
later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class DayKey:
    """A (year, day-of-year) pair plus an optional notes string."""

    year: int
    doy: int
    note: str = ""

    @property
    def date(self) -> date:
        return date(self.year, 1, 1) + timedelta(days=self.doy - 1)

    @property
    def yyyy_doy(self) -> str:
        return f"{self.year}-{self.doy:03d}"


# MVP preset — 10 days in 2023.
#
# Equinox / solstice anchors:
#   2023-03-20  → DOY 079 (March equinox)
#   2023-06-21  → DOY 172 (June solstice, low EPB rate at low latitudes)
#   2023-09-23  → DOY 266 (September equinox)
#   2023-12-22  → DOY 356 (December solstice, peak EPB season in Brazil)
#
# Geomagnetic-storm days (Kp ≥ 5) verified against NOAA SWPC/OMNIWeb logs.
MVP_DAYS_2023: tuple[DayKey, ...] = (
    DayKey(2023, 79, "March equinox - quiet"),
    DayKey(2023, 87, "March equinox - storm (Kp~5+, 2023-03-23)"),
    DayKey(2023, 172, "June solstice - quiet"),
    DayKey(2023, 200, "Quiet summer baseline"),
    DayKey(2023, 235, "Pre-equinox transition"),
    DayKey(2023, 266, "September equinox - quiet"),
    DayKey(2023, 270, "September equinox - storm (Kp~6, 2023-09-25)"),
    DayKey(2023, 311, "Pre-solstice ramp-up"),
    DayKey(2023, 339, "December storm window (Kp~7, 2023-12-05)"),
    DayKey(2023, 356, "December solstice - peak EPB season"),
)


def mvp_days() -> tuple[DayKey, ...]:
    return MVP_DAYS_2023


def _doy(year: int, month: int, day: int) -> int:
    return (date(year, month, day) - date(year, 1, 1)).days + 1


def _evenly_spaced(year: int, month_start: int, month_end_inclusive: int, every_n: int = 3) -> list[DayKey]:
    """Pick every Nth day in the month range (peak EPB season)."""
    out: list[DayKey] = []
    for m in range(month_start, month_end_inclusive + 1):
        d = 2
        while True:
            try:
                pivot = date(year, m, d)
            except ValueError:
                break
            out.append(DayKey(year, _doy(year, m, d), f"{pivot.isoformat()} season-pick"))
            d += every_n
    return out


# Phase 2-A — strategic 60-day set covering EPB peak season + Mother's Day
# 2024 super storm. Total ~480 station-days when run on 8 RBMC stations.
PHASE2A_DAYS: tuple[DayKey, ...] = tuple(
    [
        # 2023 peak season (Sep equinox → Dec solstice).
        *_evenly_spaced(2023, 9, 12, every_n=3),
        # 2024 first quarter (Jan → Mar) — solstice ramp + Feb storm window.
        *_evenly_spaced(2024, 1, 3, every_n=3),
        # May 2024 super storm (Mother's Day) — daily coverage 8–14 May.
        *[DayKey(2024, _doy(2024, 5, d), "Mother's Day storm") for d in range(8, 15)],
    ]
)


def phase2a_days() -> tuple[DayKey, ...]:
    return PHASE2A_DAYS


def storm_stratified_days(
    catalog_path: str,
    *,
    pre_days: int = 2,
    post_days: int = 3,
    quiet_doy_window: int = 15,
    require_intense: bool = True,
) -> list[DayKey]:
    """Build a storm-stratified ingest plan from a storm catalog parquet.

    For every storm in ``catalog_path`` (default: ``storm_catalog_v3.parquet``)
    that meets the intensity gate, emit:

    - ``pre_days + 1 + post_days`` storm-context days centered on the
      Dst-minimum date.
    - The same number of **quiet matched control days**: same DOY ± a few
      days in the *adjacent* year, screened to land in a calendar window
      where (a) Kp stayed below 4 all day and (b) no other catalog storm
      sits within ±5 days. Falls back gracefully if no quiet match exists.

    The output is deduplicated and sorted; the orchestrator's manifest
    handles re-run safety.
    """
    import pandas as pd

    cat = pd.read_parquet(catalog_path)
    if require_intense and "is_intense_or_stronger" in cat.columns:
        cat = cat[cat["is_intense_or_stronger"]]
    if cat.empty:
        return []

    # Storm windows — easy.
    storm_keys: list[DayKey] = []
    storm_dates: set[date] = set()
    for row in cat.itertuples():
        d0 = pd.Timestamp(row.dst_min_time).tz_convert("UTC").date()
        for offset in range(-pre_days, post_days + 1):
            d = d0 + timedelta(days=offset)
            doy = (d - date(d.year, 1, 1)).days + 1
            note = f"storm{row.storm_id}_d{offset:+d}_{row.storm_class}"
            storm_keys.append(DayKey(d.year, doy, note))
            storm_dates.add(d)

    # Quiet matched controls — for each storm date, find a quiet calendar day
    # within ± `quiet_doy_window` days of the same DOY in the adjacent year
    # that doesn't fall within ±5 d of any other storm.
    forbidden = set()
    for row in cat.itertuples():
        d0 = pd.Timestamp(row.dst_min_time).tz_convert("UTC").date()
        for offset in range(-5, 6):
            forbidden.add(d0 + timedelta(days=offset))

    quiet_keys: list[DayKey] = []
    span_yrs = sorted({d.year for d in storm_dates})
    if not span_yrs:
        return []
    yr_lo, yr_hi = span_yrs[0], span_yrs[-1]

    for storm_date in sorted(storm_dates):
        # Try +1 yr first, then -1 yr, then +2/-2.
        match = None
        for delta_y in (+1, -1, +2, -2):
            cand_year = storm_date.year + delta_y
            if not (yr_lo <= cand_year <= yr_hi + 1):
                continue
            try:
                cand0 = date(cand_year, storm_date.month, storm_date.day)
            except ValueError:
                continue
            for off in range(0, quiet_doy_window):
                for sign in (+1, -1):
                    cand = cand0 + timedelta(days=sign * off)
                    if cand in forbidden or cand in storm_dates:
                        continue
                    match = cand
                    break
                if match:
                    break
            if match:
                break
        if match:
            doy = (match - date(match.year, 1, 1)).days + 1
            quiet_keys.append(
                DayKey(match.year, doy, f"quiet-match-of-{storm_date.isoformat()}")
            )

    # Dedupe across all keys (storm + quiet) on (year, doy).
    seen: dict[tuple[int, int], DayKey] = {}
    for k in storm_keys + quiet_keys:
        key = (k.year, k.doy)
        if key not in seen:
            seen[key] = k
    return sorted(seen.values(), key=lambda k: (k.year, k.doy))
