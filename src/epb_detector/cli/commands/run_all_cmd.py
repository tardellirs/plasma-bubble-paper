"""``epb run-all`` — features → labels → snapshot → train → paper figures.

Runs the post-ingest half of the pipeline as a single command. Useful after
``epb ingest phase2a`` finishes; turns ~5 invocations into one.
"""

from __future__ import annotations

import typer
from rich import print as rprint

from epb_detector.config import SETTINGS

app = typer.Typer(no_args_is_help=True)


@app.command()
def run_all(
    features_version: str = typer.Option("v2", "--features-version"),
    labels_version: str = typer.Option("v2", "--labels-version"),
    snapshot_id: str = typer.Option("v2", "--snapshot-id"),
    model_id: str = typer.Option("xgb_v0.3.0", "--model-id"),
    skip_figures: bool = typer.Option(False, "--skip-figures"),
) -> None:
    """Build features, label them with v2 (storm-aware), snapshot, train, render figures."""
    from epb_detector.cli.commands import (
        dataset_cmd,
        features_cmd,
        labels_cmd,
        train_cmd,
    )

    rprint(f"[bold cyan]==[/] features build  → version={features_version}")
    features_cmd.build(version=features_version, out_path=None)

    rprint(f"[bold cyan]==[/] labels v2  → out={labels_version}")
    labels_cmd.label_v2(
        features_version=features_version,
        out_version=labels_version,
        features=None,
        out_path=None,
    )

    rprint(f"[bold cyan]==[/] dataset snapshot  → {snapshot_id}")
    dataset_cmd.snapshot_cmd(version=snapshot_id, labels=None)

    rprint(f"[bold cyan]==[/] train xgb  → {model_id}")
    train_cmd.train_xgb_cmd(
        version=labels_version,
        labels=None,
        model_id=model_id,
        snapshot_id=snapshot_id,
        confidence_floor=0.0,
    )

    if skip_figures:
        rprint("[yellow]skipping figures[/]")
        return

    import importlib.util

    for fig in ("make_fig10_storm_vs_quiet", "make_fig11_superposed_epoch"):
        script = SETTINGS.paths.repo_root / "paper" / "scripts" / f"{fig}.py"
        if not script.exists():
            continue
        rprint(f"[bold cyan]==[/] paper {fig}")
        spec = importlib.util.spec_from_file_location(fig, script)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            try:
                module.main(snapshot_id=snapshot_id)
            except TypeError:
                module.main()

    rprint("[bold green]done.[/]")
