"""``epb storms`` — geomagnetic-storm catalogue building.

Reads cached Dst (WDC Kyoto) + Kp/F107 (GFZ Potsdam) for an arbitrary
date range, runs the moderate-or-stronger detector, enriches each event
with sector-local-time / season / solar-cycle annotations, and persists
the result as a parquet for the storm-stratified analysis pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import typer
from rich import print as rprint

from epb_detector.config import SETTINGS
from epb_detector.external import space_weather, storms

app = typer.Typer(no_args_is_help=True)


@app.command("detect")
def detect(
    start: datetime = typer.Option(
        ..., help="Start date (UTC, YYYY-MM-DD)."
    ),
    end: datetime = typer.Option(..., help="End date (UTC, YYYY-MM-DD)."),
    threshold_nt: float = typer.Option(
        -30.0,
        help="Detection threshold for storm onset/end. Default −30 nT (moderate+).",
    ),
    min_dip_nt: float = typer.Option(
        -50.0,
        help="Minimum Dst dip to keep a storm. Default −50 (moderate+).",
    ),
    intense_threshold_nt: float = typer.Option(
        -100.0,
        help="Threshold for the is_intense_or_stronger flag (default −100 nT).",
    ),
    out: Path = typer.Option(
        None, "--out", help="Output parquet path."
    ),
) -> None:
    """Detect storms over a date range and write the enriched catalogue."""
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    rprint(f"[bold]fetching space weather[/] {start.date()} → {end.date()}")
    sw = space_weather.build_space_weather_table(start, end)
    rprint(f"  hourly rows: {len(sw):,}")

    events = storms.detect_storms(
        sw, threshold_nt=threshold_nt, min_dip_nt=min_dip_nt
    )
    rprint(f"  storms detected: {len(events)}")

    catalog = storms.enrich_storm_catalog(
        events, sw, intense_threshold_nt=intense_threshold_nt
    )
    if catalog.empty:
        rprint("[red]No storms in range. Nothing to write.[/]")
        raise typer.Exit(code=0)

    intense = int(catalog["is_intense_or_stronger"].sum())
    rprint(f"  intense+ (|Dst|≥{abs(intense_threshold_nt):.0f} nT): {intense}")
    rprint("  by lt_bin:")
    for k, v in catalog.query("is_intense_or_stronger").lt_bin.value_counts().items():
        rprint(f"    {k:14s} {int(v)}")
    rprint("  by storm_class:")
    for k, v in catalog["storm_class"].value_counts().items():
        rprint(f"    {k:10s} {int(v)}")

    out_path = out or (SETTINGS.paths.data_processed / "storm_catalog_v3.parquet")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    catalog.to_parquet(out_path, index=False)
    rprint(f"[green]Wrote[/] {out_path}  rows={len(catalog):,}")


@app.command("show")
def show(
    catalog: Path = typer.Option(
        None, help="Catalog parquet (default: data/processed/storm_catalog_v3.parquet)."
    ),
    intense_only: bool = typer.Option(False, "--intense-only"),
    n: int = typer.Option(20, help="Print at most N rows."),
) -> None:
    """Print the catalog (top of the table)."""
    cat_path = catalog or (SETTINGS.paths.data_processed / "storm_catalog_v3.parquet")
    if not cat_path.exists():
        rprint(f"[red]No catalog at[/] {cat_path}")
        raise typer.Exit(code=1)
    df = pd.read_parquet(cat_path)
    if intense_only:
        df = df[df["is_intense_or_stronger"]]
    cols = [
        "storm_id", "dst_min_time", "dst_min_value", "storm_class",
        "lt_bin", "season", "recovery_duration_hours", "solar_cycle_phase",
    ]
    rprint(df[cols].head(n).to_string())
