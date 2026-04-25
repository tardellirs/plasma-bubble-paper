"""``epb features`` — build window-level features from pyOASIS outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from rich import print as rprint
from rich.progress import track

from epb_detector.config import SETTINGS
from epb_detector.features import pipeline
from epb_detector.ingest import cache

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
) -> None:
    """Build features for every successfully ingested station-day."""
    parts: list[pd.DataFrame] = []
    for station_dir, sta, year, doy in track(_station_day_dirs(), description="features"):
        df = pipeline.build_for_station_day(station_dir, sta, year, doy)
        if not df.empty:
            parts.append(df)
    if not parts:
        rprint("[red]No features produced — is OUTPUT/ populated?[/red]")
        raise typer.Exit(code=1)
    feats = pd.concat(parts, ignore_index=True)
    out = out_path or (SETTINGS.paths.data_processed / f"features_{version}.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    feats.to_parquet(out, index=False)
    rprint(f"[green]Wrote[/] {out}  rows={len(feats):,}  sats={feats['sat'].nunique()}")
