"""``epb train`` — fit baseline classifiers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from rich import print as rprint

from epb_detector.config import SETTINGS
from epb_detector.models import xgb

app = typer.Typer(no_args_is_help=True)


@app.command("xgb")
def train_xgb_cmd(
    version: str = "v0",
    labels: Path = typer.Option(None, help="Override labels parquet path."),
    model_id: str = "xgb_v0.1.0",
    snapshot_id: str = "v0",
    confidence_floor: float = typer.Option(
        0.0,
        "--confidence-floor",
        help="Drop rows with label_confidence < floor (only used when the "
        "label parquet has the v2 schema).",
    ),
) -> None:
    """Train the XGBoost baseline."""
    label_path = labels or (SETTINGS.paths.data_processed / f"labels_{version}.parquet")
    if not label_path.exists():
        rprint(f"[red]Labels not found:[/] {label_path}")
        raise typer.Exit(code=1)
    df = pd.read_parquet(label_path)
    if "label_confidence" in df.columns and confidence_floor > 0:
        before = len(df)
        df = df[
            (df["label"] == 0) | (df["label_confidence"] >= confidence_floor)
        ].reset_index(drop=True)
        rprint(
            f"[bold]filter[/] confidence ≥ {confidence_floor}: "
            f"{before:,} → {len(df):,} rows"
        )
    trained = xgb.train_xgb(df, model_id=model_id, snapshot_id=snapshot_id)
    rprint(f"[green]Saved[/] {trained.booster_path}")
    rprint(trained.metrics.to_dict())
    if trained.metrics.pr_auc < SETTINGS.train.pr_auc_floor:
        rprint(
            f"[yellow]Warning:[/] val PR-AUC={trained.metrics.pr_auc:.3f} "
            f"< floor {SETTINGS.train.pr_auc_floor}"
        )
