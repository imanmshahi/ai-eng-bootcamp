"""Tests for the RAG-powered POST /ask — both OpenAI calls are faked."""

import math
from types import SimpleNamespace

import pytest

from server import openai_client, rag
from server.schemas import IngestRequest


# ---------------------------------------------------------------------------
# Fakes — same embedding fake as test_rag.py, plus a chat completion fake
# ---------------------------------------------------------------------------

class _FakeEmbeddings:
    def create(self, model, input):
        data = [
            SimpleNamespace(index=i, embedding=[math.cos(i), math.sin(i)])
            for i in range(len(input))
        ]
        return SimpleNamespace(data=data, usage=SimpleNamespace(total_tokens=10 * len(input)))


class _FakeChatCompletions:
    """Returns a canned answer that cites chunk IDs from the context."""

    def __init__(self):
        self.last_messages = None  # test can inspect what was sent

    def create(self, model, messages, max_tokens):
        self.last_messages = messages
        # Parse the context to find chunk IDs and cite them in the answer
        user_msg = messages[-1]["content"]
        # Extract chunk IDs from the context block
        import re
        chunk_ids = re.findall(r"\[([^\]]+#\d+)\]", user_msg)
        if chunk_ids:
            cited = ", ".join(f"[{cid}]" for cid in chunk_ids[:2])
            answer = f"Based on the documents {cited}, here is the answer."
        else:
            answer = "I don't have enough information in the provided documents to answer that."
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=answer))],
            usage=SimpleNamespace(prompt_tokens=50, completion_tokens=20, total_tokens=70),
        )


class _FakeOpenAI:
    def __init__(self, api_key):
        self.embeddings = _FakeEmbeddings()
        self.chat = SimpleNamespace(completions=_FakeChatCompletions())


@pytest.fixture(autouse=True)
def fake_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(rag, "OpenAI", _FakeOpenAI)
    monkeypatch.setattr(openai_client, "OpenAI", _FakeOpenAI)
    rag._store.clear()
    yield
    rag._store.clear()


TEXT = "RAG grounds answers in your own documents. " * 60


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_ask_empty_store_refuses():
    """No documents ingested → immediate refusal, no LLM call."""
    resp = openai_client.ask_openai("What is RAG?")
    assert resp.refused is True
    assert resp.citations == []
    assert resp.confidence == 0.0
    assert "don't have enough information" in resp.answer


def test_ask_with_context_returns_citations():
    """Documents ingested → LLM gets context, answer cites retrieved chunks."""
    rag.ingest(IngestRequest(document_id="notes.md", text=TEXT))
    resp = openai_client.ask_openai("What is RAG?")
    assert resp.refused is False
    assert len(resp.citations) > 0
    # Every citation must be a real chunk ID from the store
    for cid in resp.citations:
        assert cid in rag._store, f"citation {cid} not in store"


def test_ask_cost_includes_search():
    """cost_usd and tokens_used include both the search embedding and the LLM call."""
    rag.ingest(IngestRequest(document_id="notes.md", text=TEXT))
    resp = openai_client.ask_openai("What is RAG?")
    # Search uses 10 tokens (1 question), LLM uses 70 → total > 70
    assert resp.tokens_used > 70
    assert resp.cost_usd > 0.0


def test_ask_system_prompt_contains_refusal_instruction():
    """The system prompt tells the LLM to refuse when context doesn't cover the question."""
    assert "ONLY from the context" in openai_client._RAG_SYSTEM_PROMPT
    assert openai_client._REFUSAL in openai_client._RAG_SYSTEM_PROMPT


def test_extract_citations_filters_hallucinated():
    """Only chunk IDs that were actually retrieved survive extraction."""
    retrieved = {"a.md#0000", "a.md#0001"}
    answer = "See [a.md#0000] and [fake.md#9999] for details."
    result = openai_client._extract_citations(answer, retrieved)
    assert result == ["a.md#0000"]


def test_extract_citations_deduplicates():
    """Same chunk ID cited twice → appears once in the list."""
    retrieved = {"a.md#0000"}
    answer = "First [a.md#0000], then again [a.md#0000]."
    result = openai_client._extract_citations(answer, retrieved)
    assert result == ["a.md#0000"]
