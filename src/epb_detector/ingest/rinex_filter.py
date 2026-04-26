"""RINEX 2.11 observation file filter — keep only GPS + GLONASS records.

Modern receivers (post-2020) record GPS + GLONASS + Galileo + BeiDou + QZSS
+ NavIC simultaneously. pyOASIS only processes GPS + GLONASS, so loading the
full file via georinex spends most of its parse time on data that gets
discarded. Pre-filtering the input shrinks RINEX 2.11 obs files from ~30 MB
down to ~5 MB and roughly halves the wall-clock of every job.

The format we exploit (RINEX 2.11 obs spec, table A2):

  - Header section ends with the literal ``END OF HEADER`` token in cols 60–73.
    All header lines are passed through unchanged.

  - An *epoch* line begins with a leading space (col 1 is ``" "``) and has
    this layout::

        " YY MM DD HH MM SS.SSSSSSS  EE  NN<satlist>"
                                         ^col 30^col 33...

    where ``EE`` is the epoch flag and ``NN`` is the satellite count.
    ``satlist`` is a concatenation of 3-char PRNs (e.g. ``G05R12E03``)
    starting at column 33. If ``NN > 12``, the list overflows onto
    continuation lines indented by 32 spaces.

  - After the epoch header the file has ``NN`` *observation* lines, one per
    satellite **in the same order as ``satlist``**. Each obs line contains
    16-char numeric blocks for each observation type declared in the header.
    A satellite with more than 5 obs types overflows onto continuation
    obs-lines (still no leading PRN — the line is identified by *position*).

The filter strips Galileo / BeiDou / QZSS / NavIC PRNs from the satlist,
emits the corresponding obs lines, and recomputes ``NN``. We **do not**
rewrite the header; pyOASIS reads the obs-types declaration there and that
declaration applies system-agnostically in RINEX 2.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

KEEP_SYSTEMS = ("G", "R")  # GPS, GLONASS

# RINEX 2.11 observation lines wrap when more than 5 observation types are
# declared. The wrap count tells us how many physical lines belong to one
# logical satellite record.
def _obs_lines_per_sat(num_obs_types: int) -> int:
    return max(1, (num_obs_types + 4) // 5)


def _parse_header(lines: Iterable[str]) -> tuple[list[str], int]:
    """Return (header_lines, num_obs_types). Stops at END OF HEADER."""
    header: list[str] = []
    num_obs = 0
    for line in lines:
        header.append(line)
        if "# / TYPES OF OBSERV" in line:
            # First continuation line carries the count in cols 0-6
            with contextlib.suppress(ValueError):
                num_obs = int(line[:6].strip())
        if "END OF HEADER" in line:
            return header, num_obs
    return header, num_obs


def _parse_satlist(epoch_line: str, continuations: list[str]) -> list[str]:
    """Return PRN strings (e.g. ``"G05"``) from an epoch header + its tail."""
    # PRNs start at col 32 (0-indexed) on the header, 32 spaces of indent on
    # continuations, 3 chars each, up to 12 PRNs per line.
    chunks = [epoch_line[32:].rstrip()]
    for c in continuations:
        chunks.append(c[32:].rstrip())
    flat = "".join(chunks)
    return [flat[i : i + 3] for i in range(0, len(flat), 3)]


def _format_satlist(prns: list[str]) -> tuple[str, list[str]]:
    """Return (first_chunk, continuation_chunks) of length-≤36 each (12 PRNs)."""
    flat = "".join(prns)
    head = flat[:36]
    tail = flat[36:]
    cont: list[str] = []
    while tail:
        cont.append(tail[:36])
        tail = tail[36:]
    return head, cont


def _read_epoch(buf: list[str], cursor: int, num_obs_types: int):
    """Read one epoch starting at ``buf[cursor]``.

    Returns ``(next_cursor, header_text, prns, obs_records)`` where
    ``obs_records`` is a list of one entry per satellite in ``prns``; each
    entry is a list of physical lines (1 or 2+ depending on # of obs types).
    """
    line = buf[cursor]
    cursor += 1
    # Determine satellite count
    try:
        nsat = int(line[29:32])
    except ValueError:
        return cursor, line, [], []
    n_continuation_lines = max(0, (nsat - 12 + 11) // 12)
    continuations: list[str] = []
    for _ in range(n_continuation_lines):
        continuations.append(buf[cursor])
        cursor += 1
    prns = _parse_satlist(line, continuations)[:nsat]

    obs_lines_per_sat = _obs_lines_per_sat(num_obs_types) if num_obs_types else 1
    obs_records: list[list[str]] = []
    for _ in range(nsat):
        sat_lines: list[str] = []
        for _ in range(obs_lines_per_sat):
            if cursor >= len(buf):
                break
            sat_lines.append(buf[cursor])
            cursor += 1
        obs_records.append(sat_lines)

    header_text = "".join([line, *continuations])
    return cursor, header_text, prns, obs_records


def _emit_filtered_epoch(
    out: TextIO,
    header_line: str,
    prns: list[str],
    obs_records: list[list[str]],
) -> None:
    """Write an epoch keeping only PRNs whose system code ∈ KEEP_SYSTEMS."""
    keep_idx = [i for i, p in enumerate(prns) if p[:1] in KEEP_SYSTEMS]
    if not keep_idx:
        return
    kept_prns = [prns[i] for i in keep_idx]

    # Rewrite the epoch header — preserve everything up to col 29, replace
    # the satellite count and rewrite the satlist.
    head_chunk, cont_chunks = _format_satlist(kept_prns)
    new_first = header_line[:29] + f"{len(kept_prns):3d}" + head_chunk + "\n"
    out.write(new_first)
    for c in cont_chunks:
        out.write(" " * 32 + c + "\n")

    for i in keep_idx:
        for ln in obs_records[i]:
            out.write(ln if ln.endswith("\n") else ln + "\n")


def filter_rinex_obs(src: Path | str, dst: Path | str) -> dict[str, int]:
    """Filter ``src`` to ``dst``, keeping only GPS + GLONASS records.

    Returns a small stats dict (epochs scanned, sats kept vs dropped).
    """
    src = Path(src)
    dst = Path(dst)
    with open(src) as fh:
        raw = fh.readlines()

    header, num_obs = _parse_header(raw)
    cursor = len(header)

    stats = {"epochs": 0, "sats_kept": 0, "sats_dropped": 0}
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    with open(tmp, "w") as out:
        out.writelines(header)
        while cursor < len(raw):
            cursor, header_text, prns, obs_records = _read_epoch(raw, cursor, num_obs)
            if not prns:
                continue
            stats["epochs"] += 1
            kept = sum(1 for p in prns if p[:1] in KEEP_SYSTEMS)
            stats["sats_kept"] += kept
            stats["sats_dropped"] += len(prns) - kept
            _emit_filtered_epoch(out, header_text.split("\n", 1)[0] + "\n", prns, obs_records)

    tmp.replace(dst)
    return stats


__all__ = ["KEEP_SYSTEMS", "filter_rinex_obs"]
