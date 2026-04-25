"""``epb dataset`` — snapshot labeled features for ML/paper."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from rich import print as rprint

from epb_detector.config import SETTINGS
from epb_detector.dataset import snapshot

app = typer.Typer(no_args_is_help=True)


@app.command("snapshot")
def snapshot_cmd(
    version: str = typer.Option("v0", "--version", "-v"),
    labels: Path = typer.Option(None, help="Override labels parquet path."),
) -> None:
    """Persist a versioned training-data snapshot."""
    label_path = labels or (SETTINGS.paths.data_processed / f"labels_{version}.parquet")
    if not label_path.exists():
        rprint(f"[red]Labels not found:[/] {label_path}")
        raise typer.Exit(code=1)
    df = pd.read_parquet(label_path)
    out_dir = snapshot.write_snapshot(df, snapshot_id=version)
    rprint(f"[green]Snapshot saved to[/] {out_dir}")
    rprint(f"  meta.json, dataset_card.md, features/labels/splits parquet")
