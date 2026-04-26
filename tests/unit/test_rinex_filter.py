"""Tests for the RINEX 2.11 pre-filter (GPS + GLONASS only)."""

from __future__ import annotations

from pathlib import Path

from epb_detector.ingest.rinex_filter import filter_rinex_obs


# Minimal RINEX 2.11 obs file with mixed-constellation epochs. The exact
# column placement matters: epoch lines have ``YY MM DD HH MM SS.SSSSSSS``
# starting at col 1 with a leading space, the satellite count at cols 30-32,
# and the satellite list (3-char PRNs) starting at col 33.
def _synthetic_rinex(num_obs_types: int = 4) -> str:
    obs_decl = "    L1    L2    C1    P2"  # 4 types × 6 chars
    return (
        "     2.11           OBSERVATION DATA    M (MIXED)           RINEX VERSION / TYPE\n"
        f"{num_obs_types:6d}{obs_decl}                            # / TYPES OF OBSERV\n"
        "                                                            END OF HEADER\n"
        # Epoch 1: 4 sats, mixed G/R/E/C
        " 23  9 22  0  0  0.0000000  0  4G05R12E03C08\n"
        "  12345.678  87654.321 1234567.890 1234560.123\n"  # G05 obs
        "  22345.678 -97654.321 2234567.890 2234560.123\n"  # R12 obs
        "  32345.678  87654.321 3234567.890 3234560.123\n"  # E03 obs (drop)
        "  42345.678 -97654.321 4234567.890 4234560.123\n"  # C08 obs (drop)
        # Epoch 2: only Galileo + BeiDou — should produce no output epoch
        " 23  9 22  0  0 30.0000000  0  2E05C03\n"
        "  52345.678  87654.321 5234567.890 5234560.123\n"
        "  62345.678 -97654.321 6234567.890 6234560.123\n"
        # Epoch 3: 2 GPS only
        " 23  9 22  0  1  0.0000000  0  2G05G12\n"
        "  72345.678  87654.321 7234567.890 7234560.123\n"
        "  82345.678 -97654.321 8234567.890 8234560.123\n"
    )


def test_filter_drops_galileo_and_beidou(tmp_path: Path) -> None:
    src = tmp_path / "test.23o"
    dst = tmp_path / "test.gr.23o"
    src.write_text(_synthetic_rinex())

    stats = filter_rinex_obs(src, dst)

    body = dst.read_text()
    # E and C PRNs vanish from the output.
    assert "E03" not in body
    assert "E05" not in body
    assert "C03" not in body
    assert "C08" not in body
    # G and R PRNs survive.
    assert "G05" in body and "R12" in body and "G12" in body

    # Stats: 3 epochs scanned, 4 G/R kept, 4 E/C dropped.
    assert stats["epochs"] == 3
    assert stats["sats_kept"] == 4
    assert stats["sats_dropped"] == 4


def test_filter_rewrites_epoch_satellite_count(tmp_path: Path) -> None:
    """The ``NN`` field at cols 30–32 has to match the surviving satlist."""
    src = tmp_path / "test.23o"
    dst = tmp_path / "test.gr.23o"
    src.write_text(_synthetic_rinex())

    filter_rinex_obs(src, dst)
    lines = dst.read_text().splitlines()

    # First epoch had 4 sats (G,R,E,C); after filter, 2 (G,R).
    epoch_lines = [
        line for line in lines if line.startswith(" 23") and "0  0  0.0" in line
    ]
    assert epoch_lines, "first epoch missing"
    assert int(epoch_lines[0][29:32]) == 2

    # Third epoch had 2 GPS — should remain 2.
    epoch3 = [line for line in lines if "0  1  0.0" in line]
    assert int(epoch3[0][29:32]) == 2


def test_filter_skips_epoch_with_no_kept_systems(tmp_path: Path) -> None:
    """An all-Galileo epoch produces no output."""
    src = tmp_path / "test.23o"
    dst = tmp_path / "test.gr.23o"
    src.write_text(_synthetic_rinex())

    filter_rinex_obs(src, dst)
    body = dst.read_text()
    # Epoch 2 had only E05/C03, so its time-stamp shouldn't appear.
    assert "0  0 30.0" not in body


def test_filter_preserves_header_block_verbatim(tmp_path: Path) -> None:
    src = tmp_path / "test.23o"
    dst = tmp_path / "test.gr.23o"
    src.write_text(_synthetic_rinex())

    filter_rinex_obs(src, dst)
    body = dst.read_text()
    assert "RINEX VERSION / TYPE" in body
    assert "# / TYPES OF OBSERV" in body
    assert "END OF HEADER" in body


def test_filter_atomic_no_tmp_leftover(tmp_path: Path) -> None:
    src = tmp_path / "test.23o"
    dst = tmp_path / "test.gr.23o"
    src.write_text(_synthetic_rinex())

    filter_rinex_obs(src, dst)

    # `.tmp` sidecar must be cleaned up after the atomic rename.
    assert not (dst.with_suffix(dst.suffix + ".tmp")).exists()
    assert dst.exists()


def test_filter_handles_continuation_satlist(tmp_path: Path) -> None:
    """Epochs with > 12 satellites overflow onto a continuation line.

    The continuation is indented by 32 spaces and contains 3-char PRNs.
    """
    obs = "  12345.678  87654.321 1234567.890 1234560.123\n"
    big_epoch = (
        " 23  9 22  0  2  0.0000000  0 14"
        "G01G02G03G04G05G06G07G08G09G10G11G12\n"
        + " " * 32 + "R01E03\n"
        + obs * 14  # one obs line per sat, in order
    )
    rinex = (
        "     2.11           OBSERVATION DATA    M (MIXED)           RINEX VERSION / TYPE\n"
        "     4    L1    L2    C1    P2                            # / TYPES OF OBSERV\n"
        "                                                            END OF HEADER\n"
        + big_epoch
    )
    src = tmp_path / "test.23o"
    dst = tmp_path / "test.gr.23o"
    src.write_text(rinex)
    stats = filter_rinex_obs(src, dst)
    body = dst.read_text()

    # 12 GPS + 1 GLONASS = 13 kept, 1 Galileo dropped.
    assert stats["sats_kept"] == 13
    assert stats["sats_dropped"] == 1
    assert "E03" not in body
    assert "R01" in body
    # New count is 13 → header should declare 13 (left-padded to 3 chars).
    epoch_lines = [line for line in body.splitlines() if line.startswith(" 23  9 22  0  2")]
    assert int(epoch_lines[0][29:32]) == 13
