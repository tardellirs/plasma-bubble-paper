"""``epb predict`` — score new station-days."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from rich import print as rprint

from epb_detector.config import SETTINGS
from epb_detector.features import pipeline
from epb_detector.models import xgb

app = typer.Typer(no_args_is_help=True)


@app.command("station-day")
def predict_station_day(
    station: str,
    year: int,
    doy: int,
    model_id: str = "xgb_v0.1.0",
    out_path: Path = typer.Option(None, "--out"),
) -> None:
    """Score a single station-day already processed by pyOASIS."""
    sta = station.upper()
    station_dir = SETTINGS.paths.pyoasis_output / "RINEX" / f"{year}" / f"{doy:03d}" / sta
    if not station_dir.exists():
        rprint(f"[red]No pyOASIS output at[/] {station_dir}")
        raise typer.Exit(code=1)
    feats = pipeline.build_for_station_day(station_dir, sta, year, doy)
    if feats.empty:
        rprint("[red]No features for this station-day[/]")
        raise typer.Exit(code=1)
    proba = xgb.predict_proba(feats, model_id)
    feats["epb_probability"] = proba
    out = out_path or (
        SETTINGS.paths.data_processed
        / f"predictions/{sta}_{year}_{doy:03d}_{model_id}.parquet"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    feats.to_parquet(out, index=False)
    rprint(f"[green]Wrote[/] {out}  positive_share={(proba >= 0.5).mean():.2%}")
