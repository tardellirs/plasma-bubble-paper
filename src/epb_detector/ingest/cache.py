"""On-disk cache for ingest jobs.

Each ingested (station, year, doy) appends a row to ``cache/manifest.parquet``
with status, durations, and SHAs. Re-running the orchestrator skips entries
already marked ``ok``. The manifest is small (one row per station-day) so a
single parquet file is fine.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from epb_detector.config import SETTINGS

_MANIFEST_PATH = SETTINGS.paths.cache / "manifest.parquet"


@dataclass(slots=True)
class IngestRecord:
    """One row in the manifest."""

    sta: str
    year: int
    doy: int
    status: str  # "ok" | "skipped" | "failed"
    rinex_sha256: str | None
    sp3_sha256: str | None
    duration_s: float
    error: str | None
    completed_at: str  # ISO-8601 UTC


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> pd.DataFrame:
    if not _MANIFEST_PATH.exists():
        return pd.DataFrame(
            columns=[
                "sta",
                "year",
                "doy",
                "status",
                "rinex_sha256",
                "sp3_sha256",
                "duration_s",
                "error",
                "completed_at",
            ]
        )
    return pd.read_parquet(_MANIFEST_PATH)


def is_done(sta: str, year: int, doy: int) -> bool:
    df = load_manifest()
    if df.empty:
        return False
    mask = (df["sta"] == sta) & (df["year"] == int(year)) & (df["doy"] == int(doy)) & (
        df["status"] == "ok"
    )
    return bool(mask.any())


def append_record(record: IngestRecord) -> None:
    """Append a row, deduping by (sta, year, doy) keeping the latest status."""
    df = load_manifest()
    new_row = pd.DataFrame([asdict(record)])
    if not df.empty:
        df = df[
            ~(
                (df["sta"] == record.sta)
                & (df["year"] == record.year)
                & (df["doy"] == record.doy)
            )
        ]
    out = pd.concat([df, new_row], ignore_index=True)
    _MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(_MANIFEST_PATH, index=False)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
