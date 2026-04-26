"""Drive ingestion across many station-days.

Sequential by default (pyOASIS uses module-level state heavily, so process
parallelism is the only safe form). Set ``EPB_INGEST_WORKERS`` to >= 2 for a
``ProcessPoolExecutor`` fan-out — each worker owns its own pyOASIS import.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from epb_detector.catalog.day_selector import DayKey, mvp_days, phase2a_days
from epb_detector.catalog.stations import StationMeta, mvp_stations, phase2a_stations
from epb_detector.ingest import cache, downloader, runner

console = Console()


@dataclass(slots=True)
class IngestJob:
    sta: str
    year: int
    doy: int


def _run_one(job: IngestJob) -> cache.IngestRecord:
    t0 = time.perf_counter()
    rinex_path: Path | None = None
    sp3_path: Path | None = None
    try:
        rinex_path = downloader.fetch_rinex(job.sta, job.year, job.doy)
        sp3_path = downloader.fetch_sp3(job.year, job.doy)
        runner.run_pyoasis_pipeline(job.sta, job.year, job.doy)
        status = "ok"
        error: str | None = None
    except Exception as e:
        status = "failed"
        error = f"{type(e).__name__}: {e}"
    return cache.IngestRecord(
        sta=job.sta,
        year=job.year,
        doy=job.doy,
        status=status,
        rinex_sha256=cache.file_sha256(rinex_path) if rinex_path else None,
        sp3_sha256=cache.file_sha256(sp3_path) if sp3_path else None,
        duration_s=round(time.perf_counter() - t0, 2),
        error=error,
        completed_at=cache.utc_now_iso(),
    )


def jobs_from_mvp() -> list[IngestJob]:
    sts: list[StationMeta] = mvp_stations()
    days: tuple[DayKey, ...] = mvp_days()
    return [IngestJob(s.id, d.year, d.doy) for s in sts for d in days]


def jobs_from_phase2a() -> list[IngestJob]:
    """Phase 2-A: 8 stations × ~60 days (Sep 2023 – May 2024 EPB-peak)."""
    sts: list[StationMeta] = phase2a_stations()
    days: tuple[DayKey, ...] = phase2a_days()
    return [IngestJob(s.id, d.year, d.doy) for s in sts for d in days]


def jobs_from_storm_stratified(catalog_path: str) -> list[IngestJob]:
    """Build the storm-stratified job list from a storm catalog parquet.

    Same 8 stations as Phase 2-A; days come from
    :func:`day_selector.storm_stratified_days`.
    """
    from epb_detector.catalog.day_selector import storm_stratified_days

    sts: list[StationMeta] = phase2a_stations()
    days: list[DayKey] = storm_stratified_days(catalog_path)
    return [IngestJob(s.id, d.year, d.doy) for s in sts for d in days]


def run_jobs(jobs: list[IngestJob], force: bool = False) -> list[cache.IngestRecord]:
    pending: list[IngestJob] = []
    skipped: list[cache.IngestRecord] = []
    for j in jobs:
        if not force and cache.is_done(j.sta, j.year, j.doy):
            skipped.append(
                cache.IngestRecord(
                    j.sta, j.year, j.doy, "skipped", None, None, 0.0, None,
                    cache.utc_now_iso(),
                )
            )
            continue
        pending.append(j)

    workers = int(os.environ.get("EPB_INGEST_WORKERS", "1"))
    results: list[cache.IngestRecord] = list(skipped)
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("ingest", total=len(pending))
        if workers <= 1:
            for j in pending:
                rec = _run_one(j)
                cache.append_record(rec)
                results.append(rec)
                progress.update(
                    task, advance=1, description=f"{j.sta} {j.year}-{j.doy:03d} → {rec.status}"
                )
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_run_one, j): j for j in pending}
                for fut in as_completed(futures):
                    rec = fut.result()
                    cache.append_record(rec)
                    results.append(rec)
                    progress.update(
                        task,
                        advance=1,
                        description=f"{rec.sta} {rec.year}-{rec.doy:03d} → {rec.status}",
                    )
    return results
