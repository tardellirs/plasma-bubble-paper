"""``epb paper`` — generate publication-grade figures."""

from __future__ import annotations

import importlib
from pathlib import Path

import typer
from rich import print as rprint

app = typer.Typer(no_args_is_help=True)

PAPER_SCRIPTS_DIR = Path(__file__).resolve().parents[4] / "paper" / "scripts"


@app.command("figure")
def figure(
    name: str = typer.Argument(..., help="Figure script name, e.g. fig02_event"),
    station: str = typer.Option("SALU"),
    date: str = typer.Option("2015-12-25"),
) -> None:
    """Run a single ``paper/scripts/make_<name>.py`` script."""
    script = PAPER_SCRIPTS_DIR / f"make_{name}.py"
    if not script.exists():
        rprint(f"[red]Missing script[/]: {script}")
        raise typer.Exit(code=1)
    spec = importlib.util.spec_from_file_location(f"paper_{name}", script)  # type: ignore[attr-defined]
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load module spec")
    module = importlib.util.module_from_spec(spec)  # type: ignore[attr-defined]
    spec.loader.exec_module(module)
    if not hasattr(module, "main"):
        rprint(f"[red]{script}[/] has no main() function")
        raise typer.Exit(code=1)
    module.main(station=station, date=date)


@app.command("list")
def list_scripts() -> None:
    """List discoverable figure scripts."""
    if not PAPER_SCRIPTS_DIR.exists():
        rprint(f"[red]No paper scripts dir at[/] {PAPER_SCRIPTS_DIR}")
        raise typer.Exit(code=1)
    for f in sorted(PAPER_SCRIPTS_DIR.glob("make_*.py")):
        rprint(f"- {f.stem.removeprefix('make_')}")
