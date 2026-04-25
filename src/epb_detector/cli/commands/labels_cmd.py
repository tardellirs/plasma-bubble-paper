"""``epb labels`` — apply the weak-label heuristic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import typer
from rich import print as rprint

from epb_detector.config import SETTINGS
from epb_detector.external import space_weather, storms
from epb_detector.labels import v2_external, weak

app = typer.Typer(no_args_is_help=True)


@app.command("weak")
def label_weak(
    version: str = "v0",
    features: Path = typer.Option(None, help="Override features parquet path."),
    out_path: Path = typer.Option(None, "--out"),
) -> None:
    """Run the weak-label heuristic over a features parquet."""
    feat_path = features or (SETTINGS.paths.data_processed / f"features_{version}.parquet")
    if not feat_path.exists():
        rprint(f"[red]Features not found:[/] {feat_path}")
        raise typer.Exit(code=1)
    df = pd.read_parquet(feat_path)
    labelled = weak.label_features(df).labels
    out = out_path or (SETTINGS.paths.data_processed / f"labels_{version}.parquet")
    labelled.to_parquet(out, index=False)
    pos = int((labelled["label"] == 1).sum())
    rprint(
        f"[green]Wrote[/] {out}  rows={len(labelled):,}  positives={pos:,}  "
        f"({pos / max(1, len(labelled)) * 100:.2f}%)"
    )


@app.command("v2")
def label_v2(
    features_version: str = "v0",
    out_version: str = "v1",
    features: Path = typer.Option(None, help="Override features parquet path."),
    out_path: Path = typer.Option(None, "--out"),
) -> None:
    """Build v2 labels = weak heuristic ∪ literature cases, with confidence.

    Also attaches storm-context columns (Dst, Kp, ap, F10.7, storm_phase,
    storm_class, hours_from_dst_min) by joining with the cached space-weather
    table fetched from GFZ + WDC Kyoto.
    """
    feat_path = features or (
        SETTINGS.paths.data_processed / f"features_{features_version}.parquet"
    )
    if not feat_path.exists():
        rprint(f"[red]Features not found:[/] {feat_path}")
        raise typer.Exit(code=1)
    df = pd.read_parquet(feat_path)
    rprint(f"[bold]features[/] {feat_path.name}  rows={len(df):,}")

    # 1. Pull space weather covering the data range (+ a buffer day each side
    #    so storm phases that straddle the window can be classified).
    t0 = pd.Timestamp(df["window_start"].min()).to_pydatetime()
    t1 = pd.Timestamp(df["window_end"].max()).to_pydatetime()
    if t0.tzinfo is None:
        t0 = t0.replace(tzinfo=timezone.utc)
    if t1.tzinfo is None:
        t1 = t1.replace(tzinfo=timezone.utc)
    sw_table = space_weather.build_space_weather_table(
        t0 - timedelta(days=2), t1 + timedelta(days=2)
    )
    storm_events = storms.detect_storms(sw_table)
    sw_annotated = storms.annotate_storm_phase(sw_table, storm_events)
    rprint(
        f"[bold]space weather[/] hourly rows={len(sw_table):,}  "
        f"storms detected={len(storm_events)}"
    )

    # 2. Attach storm context to feature rows.
    enriched = storms.attach_to_features(df, sw_annotated)

    # 3. Apply v2 labels.
    labelled = v2_external.label_features_v2(enriched)

    out = out_path or (SETTINGS.paths.data_processed / f"labels_{out_version}.parquet")
    labelled.to_parquet(out, index=False)
    pos = int((labelled["label"] == 1).sum())
    by_source = labelled["label_source"].value_counts().to_dict()
    rprint(
        f"[green]Wrote[/] {out}  rows={len(labelled):,}  positives={pos:,}  "
        f"({pos / max(1, len(labelled)) * 100:.2f}%)"
    )
    rprint(f"  source breakdown: {by_source}")
