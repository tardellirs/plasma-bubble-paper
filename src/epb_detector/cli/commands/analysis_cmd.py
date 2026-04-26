"""``epb analysis`` — statistical analyses on top of model predictions."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print as rprint

from epb_detector.config import SETTINGS

app = typer.Typer(no_args_is_help=True)


@app.command("storms-v3")
def storms_v3(
    predictions: Path = typer.Option(
        None,
        help="Predictions parquet (defaults to data/processed/predictions_v3.parquet).",
    ),
    catalog: Path = typer.Option(
        None,
        help="Storm catalog parquet (defaults to data/processed/storm_catalog_v3.parquet).",
    ),
    out: Path = typer.Option(
        None,
        "--out",
        help="Output JSON (defaults to data/processed/analysis_v3.json).",
    ),
    threshold: float = typer.Option(0.5, help="EPB-probability threshold."),
    n_boot: int = typer.Option(1000, help="Bootstrap iterations."),
    model_id: str = typer.Option("xgb_v0.3.0", help="Model id stamped into the output."),
) -> None:
    """Run Q1–Q7 storm-stratified analyses and write analysis_v3.json."""
    from epb_detector.analysis import storms_v3 as ana

    pred_path = predictions or (
        SETTINGS.paths.data_processed / "predictions_v3.parquet"
    )
    cat_path = catalog or (
        SETTINGS.paths.data_processed / "storm_catalog_v3.parquet"
    )
    out_path = out or (SETTINGS.paths.data_processed / "analysis_v3.json")

    if not pred_path.exists():
        rprint(f"[red]Predictions not found:[/] {pred_path}")
        raise typer.Exit(code=1)
    if not cat_path.exists():
        rprint(f"[red]Catalog not found:[/] {cat_path}")
        raise typer.Exit(code=1)

    rprint(f"[bold]predictions[/] {pred_path}")
    rprint(f"[bold]catalog[/]     {cat_path}")
    result = ana.run_all(pred_path, cat_path, out_path=out_path, threshold=threshold, n_boot=n_boot)
    result["model_id_predicted_with"] = model_id
    out_path.write_text(json.dumps(result, indent=2, default=str))

    q1 = result["Q1_storm_vs_quiet"]
    q2 = result["Q2_lt_amplification"]
    rprint(f"[green]Wrote[/] {out_path}")
    rprint(
        f"  Q1 storm rate {q1['storm_rate_mean']:.3f} vs quiet {q1['quiet_rate_mean']:.3f}  "
        f"ratio={q1['ratio_storm_to_quiet']['ratio']:.2f}× "
        f"[{q1['ratio_storm_to_quiet']['ci_lo']:.2f}, {q1['ratio_storm_to_quiet']['ci_hi']:.2f}]"
    )
    if "two_bin" in q2:
        pa = q2["two_bin"]["PRE_adjacent"]["mean"]
        np_ = q2["two_bin"]["non_PRE"]["mean"]
        p = q2["two_bin_mannwhitney_test"]["p_one_sided_greater"]
        rprint(
            f"  Q2 PRE-adjacent {pa:.3f} vs non-PRE {np_:.3f}  "
            f"(Mann-Whitney p={p:.3f})"
        )
