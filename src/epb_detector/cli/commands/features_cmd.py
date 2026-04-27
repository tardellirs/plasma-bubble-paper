"""``epb features`` — build window-level features from pyOASIS outputs."""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import typer
from rich import print as rprint
from rich.progress import track

from epb_detector.config import SETTINGS
from epb_detector.features import pipeline
from epb_detector.ingest import cache


def _build_one(args: tuple[Path, str, int, int]) -> pd.DataFrame:
    """Process-pool worker: builds features for one station-day. Picklable."""
    station_dir, sta, year, doy = args
    return pipeline.build_for_station_day(station_dir, sta, year, doy)

app = typer.Typer(no_args_is_help=True)


def _station_day_dirs() -> list[tuple[Path, str, int, int]]:
    """Walk OUTPUT/RINEX/<year>/<doy>/<sta> for all completed station-days."""
    base = SETTINGS.paths.pyoasis_output / "RINEX"
    out: list[tuple[Path, str, int, int]] = []
    if not base.exists():
        return out
    manifest = cache.load_manifest()
    if not manifest.empty:
        ok_keys = {
            (str(r.sta), int(r.year), int(r.doy))
            for r in manifest[manifest["status"] == "ok"].itertuples()
        }
    else:
        ok_keys = set()
    for year_dir in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        for doy_dir in sorted(p for p in year_dir.iterdir() if p.is_dir()):
            for sta_dir in sorted(p for p in doy_dir.iterdir() if p.is_dir()):
                year = int(year_dir.name)
                doy = int(doy_dir.name)
                sta = sta_dir.name.upper()
                if ok_keys and (sta, year, doy) not in ok_keys:
                    continue
                out.append((sta_dir, sta, year, doy))
    return out


@app.command("build")
def build(
    version: str = "v0",
    out_path: Path = typer.Option(None, "--out", help="Override output parquet path."),
    workers: int = typer.Option(
        int(os.environ.get("EPB_FEATURES_WORKERS", "0")),
        help=(
            "Parallel worker count (0 = auto: min(8, CPU count)). "
            "Each station-day is processed independently and the partial "
            "frames are concatenated at the end. Same output as serial."
        ),
    ),
) -> None:
    """Build features for every successfully ingested station-day."""
    jobs = _station_day_dirs()
    if not jobs:
        rprint("[red]No features produced — is OUTPUT/ populated?[/red]")
        raise typer.Exit(code=1)

    n_workers = workers or min(8, (os.cpu_count() or 4))
    parts: list[pd.DataFrame] = []
    if n_workers <= 1:
        for station_dir, sta, year, doy in track(jobs, description="features"):
            df = pipeline.build_for_station_day(station_dir, sta, year, doy)
            if not df.empty:
                parts.append(df)
    else:
        rprint(f"[bold]features build[/] · {len(jobs)} station-days · {n_workers} workers")
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = {pool.submit(_build_one, j): j for j in jobs}
            for done, fut in enumerate(as_completed(futures), start=1):
                if done % 50 == 0 or done == len(jobs):
                    rprint(f"  features: {done}/{len(jobs)}")
                df = fut.result()
                if not df.empty:
                    parts.append(df)

    if not parts:
        rprint("[red]No features produced — every station-day returned empty.[/red]")
        raise typer.Exit(code=1)
    feats = pd.concat(parts, ignore_index=True)
    out = out_path or (SETTINGS.paths.data_processed / f"features_{version}.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    feats.to_parquet(out, index=False)
    rprint(f"[green]Wrote[/] {out}  rows={len(feats):,}  sats={feats['sat'].nunique()}")
