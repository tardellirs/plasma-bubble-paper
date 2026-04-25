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
