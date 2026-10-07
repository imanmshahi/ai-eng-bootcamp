"""Tests for server/rag.py ingest + search — OpenAI is faked, so no key or spend needed."""

import math
from types import SimpleNamespace

import pytest

from server import rag
from server.schemas import IngestRequest, SearchRequest


class _FakeEmbeddings:
    """Return deterministic embeddings so cosine-similarity results are predictable.

    For a list of N texts (ingest), chunk i gets the vector [cos(i), sin(i)].
    This spreads the chunks around the unit circle at 1-radian intervals:
      chunk 0 → [1.0, 0.0]   (0 rad)
      chunk 1 → [0.54, 0.84] (1 rad)
      chunk 2 → [-0.42, 0.91] (2 rad)  …etc.
    A search query with vector [1.0, 0.0] will score highest against chunk 0.
    """
    def create(self, model, input):
        data = [
            SimpleNamespace(index=i, embedding=[math.cos(i), math.sin(i)])
            for i in range(len(input))
        ]
        return SimpleNamespace(data=data, usage=SimpleNamespace(total_tokens=10 * len(input)))


class _FakeOpenAI:
    def __init__(self, api_key):
        self.embeddings = _FakeEmbeddings()


@pytest.fixture(autouse=True)
def fake_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(rag, "OpenAI", _FakeOpenAI)
    rag._store.clear()
    yield
    rag._store.clear()


TEXT = "RAG grounds answers in your own documents. " * 60  # ~2.6k chars -> several chunks


def test_ingest_same_text_twice_does_not_grow_store():
    body = IngestRequest(document_id="notes.md", text=TEXT, chunk_size=800, chunk_overlap=100)

    first = rag.ingest(body)
    second = rag.ingest(body)

    assert first.chunks_added > 1
    assert first.chunks_replaced == 0
    assert second.chunks_replaced == first.chunks_added
    assert second.total_chunks == first.total_chunks


def test_chunk_ids_are_readable_and_stable():
    rag.ingest(IngestRequest(document_id="notes.md", text=TEXT))
    assert sorted(rag._store)[:2] == ["notes.md#0000", "notes.md#0001"]


def test_shorter_reingest_removes_stale_tail_chunks():
    rag.ingest(IngestRequest(document_id="notes.md", text=TEXT))
    result = rag.ingest(IngestRequest(document_id="notes.md", text="Now just one short chunk."))
    assert result.total_chunks == 1
    assert list(rag._store) == ["notes.md#0000"]


def test_different_documents_do_not_overwrite_each_other():
    a = rag.ingest(IngestRequest(document_id="a.md", text=TEXT))
    b = rag.ingest(IngestRequest(document_id="b.md", text=TEXT))
    assert b.total_chunks == a.chunks_added + b.chunks_added


def test_document_id_is_required():
    with pytest.raises(ValueError):
        IngestRequest(text="hello")


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------

def _seed_store():
    """Ingest two documents so the store has chunks to search."""
    rag.ingest(IngestRequest(document_id="alpha.md", text=TEXT, chunk_size=800, chunk_overlap=100))
    rag.ingest(IngestRequest(document_id="beta.md", text="Something totally different. " * 40))


def test_search_returns_top_k():
    _seed_store()
    resp = rag.search(SearchRequest(question="anything", k=2))
    assert len(resp.results) == 2
    assert resp.tokens_used > 0
    assert resp.cost_usd > 0.0


def test_search_results_sorted_descending():
    _seed_store()
    resp = rag.search(SearchRequest(question="anything", k=5))
    scores = [hit.score for hit in resp.results]
    assert scores == sorted(scores, reverse=True)


def test_search_hit_fields():
    _seed_store()
    resp = rag.search(SearchRequest(question="anything", k=1))
    hit = resp.results[0]
    assert hit.chunk_id  # non-empty
    assert hit.document_id in ("alpha.md", "beta.md")
    assert isinstance(hit.score, float)
    assert len(hit.text) > 0


def test_search_empty_store():
    resp = rag.search(SearchRequest(question="anything"))
    assert resp.results == []
    assert resp.tokens_used == 0


def test_search_k_larger_than_store():
    rag.ingest(IngestRequest(document_id="tiny.md", text="one short chunk"))
    resp = rag.search(SearchRequest(question="anything", k=20))
    assert len(resp.results) == 1  # only 1 chunk exists


# ---------------------------------------------------------------------------
# Startup corpus loader tests
# ---------------------------------------------------------------------------

def test_load_corpus_ingests_txt_files(tmp_path):
    """load_corpus reads .txt files and calls ingest with filename as document_id."""
    from server.main import load_corpus, CORPUS_DIR
    import server.main as main_mod

    # Create a temp corpus dir with two files
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "DOC-001.txt").write_text("First document content.", encoding="utf-8")
    (corpus / "DOC-002.txt").write_text("Second document content.", encoding="utf-8")
    (corpus / "not-a-txt.md").write_text("Should be ignored.")

    # Point CORPUS_DIR at the temp dir
    original = main_mod.CORPUS_DIR
    main_mod.CORPUS_DIR = corpus
    try:
        load_corpus()
    finally:
        main_mod.CORPUS_DIR = original

    assert "DOC-001#0000" in rag._store
    assert "DOC-002#0000" in rag._store
    # .md file was ignored
    assert not any("not-a-txt" in cid for cid in rag._store)


def test_load_corpus_continues_on_failure(tmp_path):
    """If one file fails, the others still load."""
    from server.main import load_corpus
    import server.main as main_mod

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "AAA-good.txt").write_text("Good file.", encoding="utf-8")
    # Empty text triggers min_length=1 validation error
    (corpus / "BBB-empty.txt").write_text("", encoding="utf-8")
    (corpus / "CCC-good.txt").write_text("Another good file.", encoding="utf-8")

    original = main_mod.CORPUS_DIR
    main_mod.CORPUS_DIR = corpus
    try:
        load_corpus()  # should not raise
    finally:
        main_mod.CORPUS_DIR = original

    assert "AAA-good#0000" in rag._store
    assert "CCC-good#0000" in rag._store
