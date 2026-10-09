"""The remux writes its clusters in time order, and checks it did.

A real episode (Crunchyroll French ASS: a forced track of 9 lines, a full
one, a CC one) came out of the remux with clusters out of order: one at
3:19 written before one at 0:14. VLC skipped those blocks and the restyled
lines never showed. ffmpeg only waits 10 s for a stream by default;
`-max_interleave_delta 0` makes it wait for all of them. A synthetic file
doesn't reproduce it (the trigger is in real sources' structure), so the
fix is pinned by the command itself, and `verify` refuses any output whose
clusters go backwards.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

import bobinestyle.mux as mux_module
from bobinestyle.matroska import CLUSTER, SEGMENT, TIMESTAMP, MatroskaError, cluster_timestamps, out_of_order
from bobinestyle.mux import MuxError, mux, plan, verify
from test_mux import mkv  # noqa: F401 - fixture


def test_remux_clusters_in_time_order(mkv: Path, tmp_path: Path):  # noqa: F811
    out = mux(plan(str(mkv)), tmp_path / "out.mkv")
    stamps = cluster_timestamps(out)
    assert len(stamps) > 1
    assert out_of_order(stamps) == 0


def test_remux_waits_for_every_stream(mkv: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # noqa: F811
    commands = []
    real = mux_module.run_checked

    def spy(cmd, on_size=None):
        commands.append(cmd)
        return real(cmd, on_size)

    monkeypatch.setattr(mux_module, "run_checked", spy)
    mux(plan(str(mkv)), tmp_path / "out.mkv")
    [cmd] = commands
    i = cmd.index("-max_interleave_delta")
    assert cmd[i + 1] == "0" and i < cmd.index("-f")


def _timestamp_offsets(path: Path) -> list[tuple[int, int]]:
    """(file offset, size) of each cluster's timestamp value."""
    data = path.read_bytes()

    def vint(pos: int, keep: bool) -> tuple[int, int]:
        length = 9 - data[pos].bit_length()
        value = data[pos] if keep else data[pos] & (0xFF >> length)
        for b in data[pos + 1 : pos + length]:
            value = (value << 8) | b
        return value, pos + length

    def children(start: int, end: int):
        pos = start
        while pos < end:
            element_id, pos = vint(pos, True)
            size, pos = vint(pos, False)
            yield element_id, pos, size
            pos += size

    _, start, size = next(e for e in children(0, len(data)) if e[0] == SEGMENT)
    found = []
    for element_id, pos, length in children(start, start + size):
        if element_id == CLUSTER:
            _, value, value_size = next(e for e in children(pos, pos + length) if e[0] == TIMESTAMP)
            found.append((value, value_size))
    return found


def test_verify_refuses_clusters_out_of_order(mkv: Path, tmp_path: Path):  # noqa: F811
    p = plan(str(mkv))
    out = mux(p, tmp_path / "out.mkv")
    verify(p, str(out))  # as written: fine
    offsets = _timestamp_offsets(out)
    assert len(offsets) >= 3
    # The third cluster said to start at 0: before the second one.
    pos, size = offsets[2]
    data = bytearray(out.read_bytes())
    data[pos : pos + size] = bytes(size)
    out.write_bytes(bytes(data))
    assert out_of_order(cluster_timestamps(out)) == 1
    with pytest.raises(MuxError, match="ordre du temps"):
        verify(p, str(out))


def _element(element_id: int, payload: bytes, width: int) -> bytes:
    return element_id.to_bytes(width, "big") + bytes([0x80 | len(payload)]) + payload


def _cluster(ts: int, crc: bool = False) -> bytes:
    body = (_element(0xBF, b"\0\0\0\0", 1) if crc else b"") + _element(TIMESTAMP, bytes([ts]), 1)
    return _element(CLUSTER, body, 4)


def test_reader_skips_a_crc_and_reads_in_file_order(tmp_path: Path):
    path = tmp_path / "x.mkv"
    path.write_bytes(_element(0x1A45DFA3, b"", 4) + _element(SEGMENT, _cluster(5, crc=True) + _cluster(3), 4))
    assert cluster_timestamps(path) == [5, 3]
    assert out_of_order([5, 3]) == 1


def test_reader_unknown_size_segment(tmp_path: Path):
    """A live-written segment runs to the end of the file."""
    path = tmp_path / "x.mkv"
    body = _cluster(1) + _cluster(2)
    path.write_bytes(_element(0x1A45DFA3, b"", 4) + struct.pack(">I", SEGMENT) + b"\xff" + body)
    assert cluster_timestamps(path) == [1, 2]


def test_reader_rejects_what_it_cant_walk(tmp_path: Path):
    path = tmp_path / "x.mkv"
    path.write_bytes(b"not a matroska file")
    with pytest.raises(MatroskaError):
        cluster_timestamps(path)
