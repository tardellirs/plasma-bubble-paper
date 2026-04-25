"""``epb events`` — merge contiguous positive windows into bubble events."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from rich import print as rprint

from epb_detector.config import SETTINGS
from epb_detector.inference import events

app = typer.Typer(no_args_is_help=True)


@app.command("export")
def export(
    predictions: Path = typer.Argument(..., help="Predictions parquet (per-window probabilities)."),
    out_path: Path = typer.Option(
        None, "--out", help="Where to write the events parquet."
    ),
    min_prob: float = 0.5,
) -> None:
    """Convert per-window probabilities into discrete bubble events."""
    df = pd.read_parquet(predictions)
    out = out_path or (
        SETTINGS.paths.data_processed / f"events/{predictions.stem}_events.parquet"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    ev = events.windows_to_events(df, min_prob=min_prob)
    if ev.empty:
        # DuckDB can't read parquet files that have only the root schema; skip
        # writing instead of leaving a poison file behind.
        if out.exists():
            out.unlink()
        rprint(f"[yellow]No events ≥ {min_prob} for[/] {predictions.name}")
        return
    ev.to_parquet(out, index=False)
    rprint(f"[green]Wrote[/] {out}  events={len(ev):,}")
