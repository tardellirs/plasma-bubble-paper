"""Figure 02 — example EPB event: ROT, ROTI, ΔTEC, weak-label flag.

Renders for SALU 2015-12-25 using the data already present in
``OUTPUT/RINEX/2015/359/SALU/``. Saves PDF (vector), PNG (600 dpi), and SVG.
Updates ``paper/figures/manifest.json`` with a SHA + timestamp.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Allow `python paper/scripts/make_fig02_event.py` from repo root.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _style import COLORS, constellation_color, use  # noqa: E402

from epb_detector.config import SETTINGS  # noqa: E402
from epb_detector.io import readers  # noqa: E402

REPO = SETTINGS.paths.repo_root
FIG_DIR = SETTINGS.paths.paper_figures
MANIFEST = FIG_DIR / "manifest.json"


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_station_day(station: str, year: int, doy: int) -> dict[str, pd.DataFrame]:
    base = REPO / "OUTPUT" / "RINEX" / f"{year}" / f"{doy:03d}" / station.upper()
    out: dict[str, pd.DataFrame] = {}
    for system in ("G", "R"):
        roti_path = base / f"{station}_{doy:03d}_{year}_{system}_ROTI.txt"
        if roti_path.exists():
            out[f"roti_{system}"] = readers.read_roti(roti_path)
        dtec_path = base / f"{station}_{doy:03d}_{year}_{system}_DTEC.txt"
        if dtec_path.exists():
            out[f"dtec_{system}"] = readers.read_dtec(dtec_path)
        sidx_path = base / f"{station}_{doy:03d}_{year}_{system}_SIDX.txt"
        if sidx_path.exists():
            out[f"sidx_{system}"] = readers.read_sidx(sidx_path)
    return out


def _shaded_night(ax: "plt.Axes", t0: pd.Timestamp, t1: pd.Timestamp, lon_deg: float) -> None:
    """Shade the local-time night band 19h–06h for context."""
    one_day = pd.Timedelta(days=1)
    cursor = pd.Timestamp(t0).normalize() - one_day
    while cursor <= t1:
        offset_hours = -lon_deg / 15.0  # UT shift to local midnight
        n_start = cursor + pd.Timedelta(hours=19 + offset_hours)
        n_end = cursor + pd.Timedelta(hours=30 + offset_hours)  # next day 06h
        ax.axvspan(n_start, n_end, color=COLORS["ink"], alpha=0.05, zorder=0)
        cursor += one_day


def _format_time_axis(ax: "plt.Axes") -> None:
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_minor_locator(mdates.HourLocator())


def _render(station: str, year: int, doy: int) -> dict[str, Path]:
    data = _load_station_day(station, year, doy)
    if "roti_G" not in data:
        raise RuntimeError(f"No GPS ROTI for {station}/{year}-{doy:03d}")

    use("agu")
    fig, axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(7.0, 6.0), gridspec_kw={"hspace": 0.18}
    )

    roti_g = data["roti_G"]
    if "roti_R" in data:
        roti = pd.concat([roti_g, data["roti_R"]], ignore_index=True)
    else:
        roti = roti_g

    t0, t1 = roti["time"].min(), roti["time"].max()
    lon_mean = float(roti["Longitude"].mean())
    if lon_mean > 180:
        lon_mean -= 360

    # Panel 1 — ROTI per satellite, broken into arcs to avoid the long
    # diagonals that show up when a satellite reappears 8 h later.
    ax = axes[0]
    _shaded_night(ax, t0, t1, lon_mean)
    for sat, g in roti.groupby("SAT"):
        g = g.sort_values("time")
        gap = g["time"].diff().dt.total_seconds().fillna(0) > 600.0
        arc_id = gap.cumsum()
        for _, arc in g.groupby(arc_id):
            ax.plot(
                arc["time"],
                arc["ROTI"],
                color=constellation_color(str(sat)),
                alpha=0.55,
                linewidth=0.8,
                marker=".",
                markersize=1.2,
                label="_nolegend_",
            )
    ax.axhline(0.5, color=COLORS["warn"], linestyle="--", linewidth=0.8,
               label="0.5 TECU/min threshold")
    ax.set_ylabel("ROTI\n[TECU/min]")
    ax.set_ylim(0, max(2.0, float(roti["ROTI"].quantile(0.99) * 1.1)))
    ax.legend(loc="upper right")
    ax.set_title(f"{station} — {year}-{doy:03d}    Equatorial Plasma Bubble Diagnostics", loc="left")

    # Panel 2 — ΔTEC summary as p95 envelope across satellites in 5-min bins.
    ax = axes[1]
    if "dtec_G" in data:
        dtec = data["dtec_G"]
        bins = dtec.set_index("time")["DTEC"].resample("5min").agg(["mean", lambda s: s.abs().max()])
        bins.columns = ["mean", "abs_max"]
        ax.fill_between(bins.index, -bins["abs_max"], bins["abs_max"],
                        color=COLORS["primary"], alpha=0.15, linewidth=0)
        ax.plot(bins.index, bins["mean"], color=COLORS["primary"], linewidth=1.0)
    ax.axhline(0, color=COLORS["muted"], linewidth=0.5)
    ax.set_ylabel("ΔTEC\n[TECU/hr ×10]")

    # Panel 3 — SIDX max envelope.
    ax = axes[2]
    if "sidx_G" in data:
        sidx = data["sidx_G"]
        env = sidx.set_index("time")["SIDX"].resample("1min").max()
        ax.plot(env.index, env, color=COLORS["accent"], linewidth=1.0)
        ax.fill_between(env.index, 0, env, color=COLORS["accent"], alpha=0.18)
    ax.set_ylabel("SIDX\n[mTECU/s]")

    # Panel 4 — weak-label flag count.
    ax = axes[3]
    from epb_detector.features import pipeline  # local import to avoid circulars
    from epb_detector.labels import weak

    feats = pipeline.build_features(roti_g)
    if "dtec_G" in data:
        feats = pipeline.build_features(roti_g, dtec_df=data.get("dtec_G"))
    labelled = weak.label_features(feats).labels if not feats.empty else feats
    if "label" in labelled.columns and not labelled.empty:
        positive = labelled[labelled["label"] == 1]
        ax.scatter(
            positive["window_start"],
            np.full(len(positive), 0.5),
            color=COLORS["warn"], s=8, marker="s", label=f"weak-positive windows  (n={len(positive)})",
        )
        ax.scatter(
            labelled.loc[labelled["label"] == 0, "window_start"],
            np.full(int((labelled["label"] == 0).sum()), 0.5),
            color=COLORS["muted"], s=2, alpha=0.4, marker=".",
        )
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_ylabel("Weak label")
    ax.set_xlabel(f"UTC  ({pd.Timestamp(t0).date()})")
    ax.legend(loc="upper right")

    _format_time_axis(axes[-1])
    fig.align_ylabels(axes)

    out_paths = {
        "pdf": FIG_DIR / "fig02_event_example.pdf",
        "png": FIG_DIR / "fig02_event_example.png",
        "svg": FIG_DIR / "fig02_event_example.svg",
    }
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for ext, path in out_paths.items():
        fig.savefig(path)
    plt.close(fig)
    return out_paths


def _update_manifest(paths: dict[str, Path], station: str, year: int, doy: int) -> None:
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"figures": {}}
    entry = {
        "script": "paper/scripts/make_fig02_event.py",
        "station": station,
        "year": year,
        "doy": doy,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": {ext: str(p.relative_to(SETTINGS.paths.repo_root)) for ext, p in paths.items()},
        "sha256": {ext: _file_sha256(p) for ext, p in paths.items()},
    }
    manifest.setdefault("figures", {})["fig02_event_example"] = entry
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def main(*, station: str = "SALU", date: str = "2015-12-25") -> None:
    d = datetime.fromisoformat(date)
    year = d.year
    doy = (d - datetime(year, 1, 1)).days + 1
    paths = _render(station.upper(), year, doy)
    _update_manifest(paths, station.upper(), year, doy)
    print("Wrote:")
    for ext, p in paths.items():
        print(f"  {ext.upper()}: {p}")


if __name__ == "__main__":
    main()
