"""``epb ingest`` — pull RINEX/SP3 and run the pyOASIS pipeline."""

from __future__ import annotations

from typing import Annotated

import typer
from rich import print as rprint

from epb_detector.catalog.day_selector import mvp_days
from epb_detector.catalog.stations import get_station, mvp_stations
from epb_detector.ingest import cache as ingest_cache
from epb_detector.ingest.orchestrator import (
    IngestJob,
    jobs_from_mvp,
    jobs_from_phase2a,
    run_jobs,
)

app = typer.Typer(no_args_is_help=True)


@app.command("mvp")
def run_mvp(force: bool = False) -> None:
    """Run the MVP preset (3 stations × 10 days)."""
    recs = run_jobs(jobs_from_mvp(), force=force)
    ok = sum(r.status == "ok" for r in recs)
    fail = sum(r.status == "failed" for r in recs)
    skip = sum(r.status == "skipped" for r in recs)
    rprint(f"[bold]Ingest done[/]: ok={ok} failed={fail} skipped={skip} total={len(recs)}")


@app.command("one")
def run_one(
    station: Annotated[str, typer.Argument(help="Station ID, e.g. SALU")],
    year: Annotated[int, typer.Argument()],
    doy: Annotated[int, typer.Argument(min=1, max=366)],
    force: bool = False,
) -> None:
    """Run a single (station, year, doy)."""
    get_station(station)  # validates ID
    recs = run_jobs([IngestJob(station.upper(), year, doy)], force=force)
    rprint(recs[0])


@app.command("list")
def list_jobs() -> None:
    """Print the MVP job list."""
    rprint("[bold]Stations[/]:", [s.id for s in mvp_stations()])
    rprint("[bold]Days[/]:", [(d.year, d.doy, d.note) for d in mvp_days()])


@app.command("phase2a")
def run_phase2a(
    force: bool = False,
    skip: str = typer.Option(
        "",
        "--skip",
        help="Comma-separated station IDs to exclude (e.g. BOAV,POAL).",
    ),
) -> None:
    """Run the Phase 2-A preset (8 stations × ~60 days, Sep 2023 → May 2024)."""
    skip_set = {s.strip().upper() for s in skip.split(",") if s.strip()}
    all_jobs = jobs_from_phase2a()
    jobs = [j for j in all_jobs if j.sta not in skip_set]
    if skip_set:
        rprint(
            f"[yellow]Skipping[/] stations: {sorted(skip_set)}  "
            f"(removed {len(all_jobs) - len(jobs)} jobs)"
        )
    rprint(
        f"[bold]Phase 2-A[/]: {len(jobs)} station-days  "
        f"({len({j.sta for j in jobs})} stations × {len({(j.year, j.doy) for j in jobs})} days)"
    )
    recs = run_jobs(jobs, force=force)
    ok = sum(r.status == "ok" for r in recs)
    fail = sum(r.status == "failed" for r in recs)
    skipped_count = sum(r.status == "skipped" for r in recs)
    rprint(f"[bold]Done[/]: ok={ok} failed={fail} skipped={skipped_count} total={len(recs)}")


@app.command("status")
def status() -> None:
    """Print the current ingest manifest grouped by status."""
    df = ingest_cache.load_manifest()
    if df.empty:
        rprint("[yellow]No manifest yet — nothing has been ingested.[/]")
        return
    counts = df["status"].value_counts().to_dict()
    rprint(f"[bold]Manifest[/]: {len(df)} rows  →  {counts}")
    if "duration_s" in df.columns:
        d = df.loc[df["status"] == "ok", "duration_s"]
        if not d.empty:
            rprint(
                f"  ok runs: median {d.median():.1f}s · p90 {d.quantile(0.9):.1f}s "
                f"· total {d.sum() / 60:.1f} min"
            )
    failed = df[df["status"] == "failed"]
    if not failed.empty:
        rprint(f"\n[red]Failures ({len(failed)}):[/]")
        for _, r in failed.head(10).iterrows():
            err = (r.get("error") or "")[:120].replace("\n", " ")
            rprint(f"  {r['sta']} {r['year']}-{int(r['doy']):03d} → {err}")
