"""Loader for the curated literature EPB case-study list."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date
from datetime import datetime
from functools import cache
from importlib.resources import files

import pandas as pd
import yaml


@dataclass(frozen=True, slots=True)
class CaseEvent:
    date: _date
    stations: tuple[str, ...]
    reference: str
    doi: str
    notes: str

    @property
    def doy(self) -> int:
        return (self.date - _date(self.date.year, 1, 1)).days + 1


@cache
def load_cases() -> tuple[CaseEvent, ...]:
    raw = files("epb_detector.external").joinpath("case_studies.yaml").read_text()
    payload = yaml.safe_load(raw)
    return tuple(
        CaseEvent(
            date=e["date"] if isinstance(e["date"], _date) else datetime.fromisoformat(e["date"]).date(),
            stations=tuple(s.upper() for s in e.get("stations", [])),
            reference=str(e.get("reference", "")),
            doi=str(e.get("doi", "")),
            notes=str(e.get("notes", "")),
        )
        for e in payload.get("events", [])
    )


def cases_for(station: str, year: int, doy: int) -> list[CaseEvent]:
    sta = station.upper()
    out = []
    for ev in load_cases():
        if sta in ev.stations and ev.date.year == year and ev.doy == doy:
            out.append(ev)
    return out


def to_dataframe() -> pd.DataFrame:
    rows = []
    for ev in load_cases():
        for sta in ev.stations:
            rows.append(
                {
                    "date": pd.Timestamp(ev.date, tz="UTC"),
                    "year": ev.date.year,
                    "doy": ev.doy,
                    "station": sta,
                    "reference": ev.reference,
                    "doi": ev.doi,
                    "notes": ev.notes,
                }
            )
    return pd.DataFrame(rows)
