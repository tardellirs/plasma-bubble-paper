"""Top-level Typer app for the ``epb`` command-line."""

from __future__ import annotations

import typer

from epb_detector.cli.commands import (
    analysis_cmd,
    dataset_cmd,
    events_cmd,
    features_cmd,
    ingest_cmd,
    labels_cmd,
    paper_cmd,
    predict_cmd,
    run_all_cmd,
    storms_cmd,
    train_cmd,
)

app = typer.Typer(
    no_args_is_help=True,
    help="Equatorial plasma bubble detector — bulk ingest, train, serve.",
    rich_markup_mode="rich",
)

app.add_typer(ingest_cmd.app, name="ingest", help="Download + run pyOASIS for many station-days.")
app.add_typer(features_cmd.app, name="features", help="Build window-level feature parquet.")
app.add_typer(labels_cmd.app, name="labels", help="Apply the weak-label heuristic.")
app.add_typer(train_cmd.app, name="train", help="Train models on labeled features.")
app.add_typer(predict_cmd.app, name="predict", help="Score new station-days with a trained model.")
app.add_typer(events_cmd.app, name="events", help="Convert window scores into bubble events.")
app.add_typer(dataset_cmd.app, name="dataset", help="Snapshot the labeled dataset for ML/paper.")
app.add_typer(paper_cmd.app, name="paper", help="Render publication figures.")
app.add_typer(run_all_cmd.app, name="run-all", help="Post-ingest pipeline: features→labels→snapshot→train→figures.")
app.add_typer(storms_cmd.app, name="storms", help="Build geomagnetic-storm catalogues for analysis.")
app.add_typer(analysis_cmd.app, name="analysis", help="Statistical analyses on predictions parquets.")


if __name__ == "__main__":  # pragma: no cover
    app()
