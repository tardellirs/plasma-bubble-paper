"""Shared matplotlib style for all publication figures.

Three presets:
- ``agu`` — single-column AGU/JGR submission (3.5 in wide).
- ``ieee`` — IEEE single-column (3.5 in wide).
- ``slides_dark`` — 16:9 dark theme for the conference talk.

Usage:
    from _style import use, COLORS
    use("agu")
    fig, ax = plt.subplots(figsize=(3.5, 2.2))
"""

from __future__ import annotations

from typing import Literal

import matplotlib as mpl
import matplotlib.pyplot as plt

Preset = Literal["agu", "ieee", "slides_dark"]


COLORS: dict[str, str] = {
    # Curated palette for ROTI / TEC heat maps and category coding.
    "primary": "#0FA3B1",       # cyan-teal — neutral / good
    "accent": "#F7A072",        # warm orange — highlight
    "warn": "#E63946",          # red — anomaly
    "muted": "#6C757D",
    "ink": "#0B132B",
    "paper": "#FAFAFC",
    "grid": "#D9D9DE",
    # Constellation coding for ROT/ROTI plots.
    "gps": "#0FA3B1",
    "glonass": "#9B5DE5",
    "galileo": "#FFC857",
    "beidou": "#E63946",
}


_BASE: dict[str, object] = {
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.linewidth": 0.5,
    "grid.alpha": 0.5,
    "axes.labelpad": 4,
    "axes.titlesize": 9,
    "axes.titleweight": "bold",
    "axes.titlepad": 6,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "legend.frameon": False,
    "lines.linewidth": 1.2,
    "lines.solid_capstyle": "round",
    "savefig.bbox": "tight",
    "savefig.dpi": 600,
    "pdf.fonttype": 42,  # vector text in PDF
    "ps.fonttype": 42,
    "font.family": "sans-serif",
    "font.sans-serif": ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans"],
}


_PRESETS: dict[Preset, dict[str, object]] = {
    "agu": {
        **_BASE,
        "figure.figsize": (3.5, 2.6),
        "axes.facecolor": COLORS["paper"],
        "axes.edgecolor": COLORS["ink"],
        "axes.labelcolor": COLORS["ink"],
        "text.color": COLORS["ink"],
        "xtick.color": COLORS["ink"],
        "ytick.color": COLORS["ink"],
        "grid.color": COLORS["grid"],
    },
    "ieee": {
        **_BASE,
        "figure.figsize": (3.5, 2.4),
        "axes.facecolor": "white",
        "axes.edgecolor": "black",
        "grid.color": "#CCCCCC",
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
    },
    "slides_dark": {
        **_BASE,
        "figure.figsize": (10.5, 5.9),
        "axes.facecolor": "#0E1117",
        "figure.facecolor": "#0B132B",
        "axes.edgecolor": "#FAFAFC",
        "axes.labelcolor": "#FAFAFC",
        "text.color": "#FAFAFC",
        "xtick.color": "#FAFAFC",
        "ytick.color": "#FAFAFC",
        "grid.color": "#2A3045",
    },
}


def use(preset: Preset = "agu") -> None:
    if preset not in _PRESETS:
        raise KeyError(f"Unknown preset: {preset}")
    mpl.rcdefaults()
    plt.rcParams.update(_PRESETS[preset])


def constellation_color(code: str) -> str:
    if code.startswith("G"):
        return COLORS["gps"]
    if code.startswith("R"):
        return COLORS["glonass"]
    if code.startswith("E"):
        return COLORS["galileo"]
    if code.startswith("C"):
        return COLORS["beidou"]
    return COLORS["muted"]
