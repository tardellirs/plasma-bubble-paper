#!/usr/bin/env python3
"""
download_inputs.py — Fetch RINEX observation + MGEX SP3 orbit for OASIS.

RINEX comes from the Brazilian IBGE RBMC archive (no login, lowercase station
codes). MGEX SP3 orbits come from IGN (no login) with GFZ as fallback. Outputs
are placed in INPUT/RINEX and INPUT/ORBITS, ready for `python main.py`.

Usage:
    python download_inputs.py STATION YEAR DOY

Example:
    python download_inputs.py BOAV 2023 049
"""
import argparse
import gzip
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
import zipfile
from datetime import datetime, timedelta
from pathlib import Path


def gps_week(year: int, doy: int) -> int:
    date = datetime(year, 1, 1) + timedelta(days=doy - 1)
    gps_epoch = datetime(1980, 1, 6)
    return (date - gps_epoch).days // 7


def download(url: str, dest: Path, timeout: int = 120) -> bool:
    print(f"  GET {url}")
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "OASIS-downloader/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        size = dest.stat().st_size
        print(f"  OK ({size/1024:.1f} KB)")
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
        print(f"  ! {e}")
        if dest.exists():
            dest.unlink()
        return False


def gunzip(src: Path, dest: Path) -> None:
    with gzip.open(src, "rb") as gz, open(dest, "wb") as out:
        shutil.copyfileobj(gz, out)
    src.unlink()


def uncompress_z(src: Path, dest: Path) -> None:
    """Decompress an LZW .Z file via gunzip/uncompress and write to dest."""
    for tool in ("gunzip", "uncompress"):
        if shutil.which(tool):
            subprocess.run([tool, "-f", str(src)], check=True)
            produced = src.with_suffix("")  # strips ".Z"
            produced.rename(dest)
            return
    raise RuntimeError(
        "Need 'gunzip' or 'uncompress' on PATH to decompress legacy .Z SP3 files."
    )


def fetch_sp3(year: int, doy: int, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    week = gps_week(year, doy)
    # MGEX file naming changed over time. Try known prefixes in order of recency.
    # After ~Nov 2022 (week 2238), IGS switched to IGS20 frame and GFZ renamed
    # its product from GFZ0MGXRAP_ to GBM0MGXRAP_; path also gained _IGS20 suffix.
    prefixes = ["GBM0MGXRAP", "GFZ0MGXRAP", "JAX0MGXFIN"]
    week_dirs = [f"{week}_IGS20", f"{week}"]
    hosts = [
        "ftp://ftp.gfz-potsdam.de/home/GNSS/products/mgex",
        "ftp://igs.ensg.ign.fr/pub/igs/products/mgex",
    ]

    for prefix in prefixes:
        name = f"{prefix}_{year}{doy:03d}0000_01D_05M_ORB.SP3"
        dest = out_dir / name
        if dest.exists():
            print(f"SP3 already present: {dest.name}")
            return dest

    for prefix in prefixes:
        name = f"{prefix}_{year}{doy:03d}0000_01D_05M_ORB.SP3"
        dest = out_dir / name
        gz_name = name + ".gz"
        tmp = out_dir / gz_name
        for host in hosts:
            for week_dir in week_dirs:
                url = f"{host}/{week_dir}/{gz_name}"
                if download(url, tmp):
                    gunzip(tmp, dest)
                    print(f"SP3 saved: {dest}")
                    return dest

    # Fallback: pre-2018 MGEX archive uses legacy short names like
    # gbm{week}{dow}.sp3.Z (LZW-compressed). Try a few analysis-center
    # prefixes; promote the result to the modern long-form filename so the
    # rest of the pipeline finds it via the standard *.SP3 glob.
    date = datetime(year, 1, 1) + timedelta(days=doy - 1)
    dow = (date - datetime(1980, 1, 6)).days % 7
    legacy_prefixes = ["gbm", "com", "wum", "grm", "tum"]
    long_dest = out_dir / f"GBM0MGXRAP_{year}{doy:03d}0000_01D_05M_ORB.SP3"
    for ac in legacy_prefixes:
        short = f"{ac}{week}{dow}.sp3.Z"
        for host in hosts:
            url = f"{host}/{week}/{short}"
            tmp = out_dir / short
            if download(url, tmp):
                uncompress_z(tmp, long_dest)
                print(f"SP3 saved: {long_dest}  (from legacy {short})")
                return long_dest

    raise RuntimeError(
        f"Could not download SP3 orbit for year={year} doy={doy:03d} (GPS week {week})."
    )


def fetch_rinex_ibge(station: str, year: int, doy: int, out_dir: Path) -> Path:
    """Fetch RBMC RINEX observation from IBGE. Station codes are lowercase."""
    out_dir.mkdir(parents=True, exist_ok=True)
    station_l = station.lower()
    yy = year % 100
    obs_name = f"{station_l}{doy:03d}1.{yy:02d}o"
    dest = out_dir / obs_name
    if dest.exists():
        print(f"RINEX already present: {dest.name}")
        return dest
    zip_name = f"{station_l}{doy:03d}1.zip"
    url = (
        f"https://geoftp.ibge.gov.br/informacoes_sobre_posicionamento_geodesico"
        f"/rbmc/dados/{year}/{doy:03d}/{zip_name}"
    )
    tmp = out_dir / zip_name
    if not download(url, tmp):
        raise RuntimeError(
            f"RINEX not found at IBGE RBMC for {station.upper()} {year}/{doy:03d}. "
            f"Note: IBGE only hosts Brazilian RBMC stations."
        )
    extracted_obs = None
    with zipfile.ZipFile(tmp) as z:
        for member in z.namelist():
            mlow = member.lower()
            if mlow.endswith(f".{yy:02d}o") or mlow.endswith(f".{yy:02d}d"):
                z.extract(member, out_dir)
                extracted_obs = out_dir / member
                break
    tmp.unlink()
    if extracted_obs is None:
        raise RuntimeError(f"No observation file found inside {zip_name}")
    if extracted_obs.suffix.lower() == f".{yy:02d}d":
        # Hatanaka-compressed → decompress via georinex's hatanaka helper
        try:
            import hatanaka
            hatanaka.decompress_on_disk(extracted_obs)
        except Exception as e:
            raise RuntimeError(f"Failed to decompress Hatanaka file: {e}")
        crx_file = extracted_obs
        extracted_obs = extracted_obs.with_suffix(f".{yy:02d}o")
        if crx_file.exists() and crx_file != extracted_obs:
            crx_file.unlink()
    if extracted_obs != dest:
        extracted_obs.rename(dest)
    print(f"RINEX saved: {dest}")
    return dest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("station", help="Station code, e.g. BOAV")
    p.add_argument("year", type=int, help="Four-digit year, e.g. 2023")
    p.add_argument("doy", type=int, help="Day of year, 1–366")
    p.add_argument(
        "--rinex-dir",
        default="INPUT/RINEX",
        help="RINEX output directory (default: INPUT/RINEX)",
    )
    p.add_argument(
        "--orbit-dir",
        default="INPUT/ORBITS",
        help="Orbit output directory (default: INPUT/ORBITS)",
    )
    args = p.parse_args()

    base = Path(__file__).resolve().parent
    rinex_dir = (base / args.rinex_dir).resolve()
    orbit_dir = (base / args.orbit_dir).resolve()
    print(f"Station: {args.station.upper()}  Year: {args.year}  DOY: {args.doy:03d}")
    print(f"RINEX dir: {rinex_dir}")
    print(f"Orbit dir: {orbit_dir}")
    print()
    print("[1/2] RINEX observation")
    fetch_rinex_ibge(args.station, args.year, args.doy, rinex_dir)
    print()
    print("[2/2] MGEX SP3 orbit")
    fetch_sp3(args.year, args.doy, orbit_dir)
    print()
    print("Done. You can now run: python main.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
