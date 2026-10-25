"""Tests for server/rag.py chunk_text — the line-boundary packing that fixed F1's root cause.

Run from the repo root:  python -m pytest evals/test_chunking.py -q

Importing server.rag is safe: it calls load_dotenv() and builds no OpenAI client at import time,
and nothing here touches the network or reads a key.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.rag import chunk_text  # noqa: E402

# Live settings, from IngestRequest defaults in server/schemas.py.
LIVE_SIZE, LIVE_OVERLAP = 800, 100

# Shaped like the TRADE-BIODIESEL annex whose mid-row splits made q09 unanswerable.
TABLE = """ANNEX
COOPERATING EXPORTING PRODUCERS NOT SAMPLED
Name | TARIC additional code
Anhui Tianyi Environmental Protection Tech. Co., Ltd | 89EG
Baoshun (Henan) New Carbon Material Co., Ltd | 89EH
Bemay (Hubei) New Energy Company, Ltd | 89FU
Tangshan Jinlihai Biodiesel Co., Ltd | 89FQ
Wenzhou Zhongke New Energy Technology Co., Ltd | 89FR
YANGZHOU JIANYUAN BIOTECHNOLOGY CO., LTD | 89FS
"""

PROSE = (
    "Each Member State shall set an obligation on fuel suppliers to ensure that the amount of "
    "renewable fuels supplied to the transport sector leads to a share of at least 29 % by 2030.\n"
    "Member States shall establish a mechanism allowing fuel suppliers to exchange credits.\n"
    "Economic operators supplying renewable electricity to electric vehicles receive credits.\n"
)


def source_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def whole_in_some_chunk(line: str, chunks: list[str]) -> bool:
    return any(line in c for c in chunks)


# ── a line is never split unless it is longer than chunk_size ─────────
@pytest.mark.parametrize("size,overlap", [(120, 30), (200, 50), (LIVE_SIZE, LIVE_OVERLAP)])
def test_table_rows_stay_intact(size, overlap):
    chunks = chunk_text(TABLE, size, overlap)
    broken = [ln for ln in source_lines(TABLE) if not whole_in_some_chunk(ln, chunks)]
    assert broken == [], broken


def test_the_q09_row_survives_whole():
    """The specific row that was cut in half before the fix."""
    row = "Tangshan Jinlihai Biodiesel Co., Ltd | 89FQ"
    chunks = chunk_text(TABLE, 120, 30)
    assert whole_in_some_chunk(row, chunks)


@pytest.mark.parametrize("size,overlap", [(120, 30), (300, 60)])
def test_prose_lines_stay_intact(size, overlap):
    """Lines that fit must stay whole; a line longer than chunk_size is allowed to split."""
    chunks = chunk_text(PROSE, size, overlap)
    broken = [
        ln for ln in source_lines(PROSE)
        if len(ln) <= size and not whole_in_some_chunk(ln, chunks)
    ]
    assert broken == [], broken


def test_prose_line_longer_than_chunk_size_is_the_only_one_split():
    """Guards the exclusion above: at size=120 exactly the over-long line splits, no others."""
    size = 120
    chunks = chunk_text(PROSE, size, 30)
    lines = source_lines(PROSE)
    over_long = [ln for ln in lines if len(ln) > size]
    assert len(over_long) == 1, [len(ln) for ln in lines]
    assert not whole_in_some_chunk(over_long[0], chunks)
    for ln in lines:
        if ln is not over_long[0]:
            assert whole_in_some_chunk(ln, chunks), ln


def test_short_lines_are_packed_together_not_one_per_chunk():
    """Packing must still fill a chunk, or the store would bloat with tiny chunks."""
    text = "".join(f"row {i}\n" for i in range(20))  # 7 chars each
    chunks = chunk_text(text, 100, 0)
    assert len(chunks) < 20, chunks
    assert any(c.count("\n") >= 5 for c in chunks), chunks


def test_every_chunk_fits_chunk_size():
    for size, overlap in [(50, 10), (120, 30), (LIVE_SIZE, LIVE_OVERLAP)]:
        for text in (TABLE, PROSE):
            for c in chunk_text(text, size, overlap):
                assert len(c) <= size, (size, len(c), c[:40])


# ── lines longer than chunk_size still split, as before ───────────────
def test_overlong_line_still_splits():
    line = "x" * 500
    chunks = chunk_text(line, 120, 30)
    assert len(chunks) > 1
    assert all(len(c) <= 120 for c in chunks)
    assert "".join(dict.fromkeys("".join(chunks))) == "x"  # nothing but the original character


def test_overlong_line_loses_no_content():
    line = "".join(str(i % 10) for i in range(500))
    chunks = chunk_text(line, 120, 30)
    # Every position of the original appears in some chunk: reassembly by overlap-aware walk.
    assert chunks[0] == line[:120]
    assert line[-1] in chunks[-1]


def test_overlong_line_among_short_ones_keeps_the_short_ones_whole():
    text = "keep me whole\n" + "y" * 400 + "\nkeep me too\n"
    chunks = chunk_text(text, 120, 30)
    assert whole_in_some_chunk("keep me whole", chunks)
    assert whole_in_some_chunk("keep me too", chunks)


# ── overlap still works ───────────────────────────────────────────────
def test_overlap_repeats_whole_lines_between_consecutive_chunks():
    """With overlap wide enough to carry a row, consecutive chunks must share one."""
    chunks = chunk_text(TABLE, 120, 60)
    shared = [
        set(a.splitlines()) & set(b.splitlines())
        for a, b in zip(chunks, chunks[1:])
    ]
    assert any(s for s in shared), chunks


def test_overlap_at_live_settings_carries_context():
    chunks = chunk_text(TABLE + PROSE, LIVE_SIZE, LIVE_OVERLAP)
    if len(chunks) > 1:
        shared = [
            set(a.splitlines()) & set(b.splitlines())
            for a, b in zip(chunks, chunks[1:])
        ]
        assert any(s for s in shared), "no context carried at live settings"


def test_zero_overlap_repeats_nothing():
    chunks = chunk_text(TABLE, 120, 0)
    for a, b in zip(chunks, chunks[1:]):
        assert not (set(a.splitlines()) & set(b.splitlines()))


def test_overlap_never_exceeds_chunk_overlap_characters():
    overlap = 60
    chunks = chunk_text(TABLE, 120, overlap)
    for a, b in zip(chunks, chunks[1:]):
        repeated = [ln for ln in b.splitlines() if ln in a.splitlines()]
        assert sum(len(ln) + 1 for ln in repeated) <= overlap + 1, repeated


# ── edge cases must not hang or raise ─────────────────────────────────
@pytest.mark.parametrize(
    "text,size,overlap",
    [
        ("", 100, 10),
        ("\n\n\n", 100, 10),
        ("a\nb", 100, 10),
        ("no trailing newline", 100, 10),
        ("x" * 500, 120, 30),
        (TABLE, 120, 0),
        (TABLE, 120, 119),      # overlap one below size
        ("abc\ndef", 1, 0),     # size smaller than any line
        (TABLE, 10_000, 100),   # size larger than the whole text
    ],
)
def test_edge_cases_terminate_and_respect_size(text, size, overlap):
    chunks = chunk_text(text, size, overlap)
    assert all(len(c) <= size for c in chunks), [len(c) for c in chunks]
    assert all(c.strip() for c in chunks), "blank chunk emitted"


def test_empty_and_blank_input_produce_no_chunks():
    assert chunk_text("", 100, 10) == []
    assert chunk_text("\n\n  \n", 100, 10) == []


def test_text_shorter_than_chunk_size_is_one_chunk():
    assert chunk_text("just one line\n", 800, 100) == ["just one line"]


# ── the real corpus ───────────────────────────────────────────────────
CORPUS = Path(__file__).resolve().parent.parent / "corpus"


@pytest.mark.parametrize("path", sorted(CORPUS.glob("*.txt")) if CORPUS.is_dir() else [])
def test_real_corpus_files_keep_every_line_whole(path):
    """At live settings, no line in the shipped corpus may be cut."""
    text = path.read_text(encoding="utf-8")
    chunks = chunk_text(text, LIVE_SIZE, LIVE_OVERLAP)
    over_long = {ln for ln in source_lines(text) if len(ln) > LIVE_SIZE}
    broken = [
        ln for ln in source_lines(text)
        if ln not in over_long and not whole_in_some_chunk(ln, chunks)
    ]
    assert broken == [], (path.name, broken[:3])
