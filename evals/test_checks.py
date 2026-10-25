"""Unit tests for evals/checks.py — hand-made traces only, never the real trace file.

Run from the repo root:  python -m pytest evals/test_checks.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.checks import (  # noqa: E402
    check_citations_were_retrieved,
    check_declined_despite_retrieval,
    check_no_uncited_numbers,
    check_over_refusal,
    check_refusal_consistency,
    declined,
    hedges_in,
    ids_in_prose,
    over_refusal_rate,
    run_all,
)

REFUSAL = "I don't have enough information in the provided documents to answer that."


def trace(**kw):
    """A valid, passing trace; override any field per test."""
    base = {
        "id": "t00",
        "question": "q?",
        "answer": "The share is 29% [DOC-A#0000].",
        "citations": ["DOC-A#0000"],
        "refused": False,
        "tokens_used": 100,
        "retrieved": [
            {"chunk_id": f"DOC-A#000{i}", "document_id": "DOC-A", "score": 0.6 - i / 100}
            for i in range(5)
        ],
    }
    base.update(kw)
    return base


# ── helper ────────────────────────────────────────────────────────────
def test_ids_in_prose_finds_and_dedupes():
    answer = "a [DOC-A#0000] b [DOC-B#0012] c [DOC-A#0000]"
    assert ids_in_prose(answer) == ["DOC-A#0000", "DOC-B#0012"]


def test_ids_in_prose_ignores_non_ids():
    assert ids_in_prose("see Article 27(1), point (b) and [not an id]") == []


# ── check 1: citations_were_retrieved (C3) ────────────────────────────
def test_citations_pass_when_all_retrieved():
    passed, reason = check_citations_were_retrieved(trace())
    assert passed, reason


def test_citations_fail_on_invented_id_in_prose():
    """The F3 shape: citations field is clean, the prose carries an unretrieved ID."""
    t = trace(answer="Member States must act [DOC-A#0099].", citations=["DOC-A#0000"])
    passed, reason = check_citations_were_retrieved(t)
    assert not passed
    assert "DOC-A#0099" in reason and "prose" in reason


def test_citations_fail_on_invented_id_in_field():
    t = trace(citations=["DOC-A#0000", "DOC-Z#0001"])
    passed, reason = check_citations_were_retrieved(t)
    assert not passed
    assert "DOC-Z#0001" in reason and "citations" in reason


def test_citations_pass_when_nothing_cited():
    t = trace(answer=REFUSAL, citations=[], refused=True)
    passed, reason = check_citations_were_retrieved(t)
    assert passed
    assert "nothing to verify" in reason


# ── check 2: refusal_consistency (F2 class) ───────────────────────────
def test_refusal_consistency_ok_when_refused_and_empty():
    passed, _ = check_refusal_consistency(trace(answer=REFUSAL, citations=[], refused=True))
    assert passed


def test_refusal_consistency_ok_when_answered_and_cited():
    passed, _ = check_refusal_consistency(trace())
    assert passed


def test_refusal_consistency_fails_when_refused_but_cites():
    passed, reason = check_refusal_consistency(trace(refused=True))
    assert not passed
    assert "refused=True but cites" in reason


def test_refusal_consistency_fails_on_the_f2_state():
    """refused=False with no citations — the confident, ungrounded answer from F2."""
    t = trace(answer="Probably about 30%.", citations=[], refused=False)
    passed, reason = check_refusal_consistency(t)
    assert not passed
    assert "no grounding" in reason


# ── check 3: no_uncited_numbers (C2) ──────────────────────────────────
def test_uncited_numbers_fails_on_percentage_without_citation():
    t = trace(answer="The target is 29% by 2030.", citations=[])
    passed, reason = check_no_uncited_numbers(t)
    assert not passed
    assert "29%" in reason


def test_uncited_numbers_catches_eu_comma_decimals():
    """The corpus writes rates as '35,6 %' — the check must see that form too."""
    t = trace(answer="The duty is 35,6 % for that group.", citations=[])
    passed, reason = check_no_uncited_numbers(t)
    assert not passed
    assert "35,6 %" in reason


def test_uncited_numbers_catches_decimal_rate_without_percent_sign():
    t = trace(answer="A rate of 21,7 applies.", citations=[])
    passed, reason = check_no_uncited_numbers(t)
    assert not passed
    assert "21,7" in reason


def test_uncited_numbers_passes_when_cited():
    passed, _ = check_no_uncited_numbers(trace(answer="29% [DOC-A#0000]."))
    assert passed


def test_uncited_numbers_ignores_years_and_article_numbers():
    """Bare integers must not fire, or every answer mentioning 2030 would fail."""
    t = trace(answer="By 2030, under Article 27(1), point (b), suppliers must comply.", citations=[])
    passed, reason = check_no_uncited_numbers(t)
    assert passed, reason


def test_uncited_numbers_passes_on_refusal():
    passed, _ = check_no_uncited_numbers(trace(answer=REFUSAL, citations=[], refused=True))
    assert passed


# ── check 4: declined_despite_retrieval (C2) ──────────────────────────
@pytest.mark.parametrize(
    "hedge",
    ["not detailed", "not explicitly", "not specified", "does not specify", "not mentioned"],
)
def test_declined_flags_each_hedge_with_five_chunks(hedge):
    t = trace(answer=f"The 2030 share is {hedge} in the provided context [DOC-A#0000].")
    passed, reason = check_declined_despite_retrieval(t)
    assert not passed
    assert hedge in reason and "5 chunks" in reason


@pytest.mark.parametrize(
    "wording",
    [
        # Each of these is the same concession. The literal phrase list caught only some, which
        # is how q12 looked "fixed" in v2 while still hedging.
        "is not detailed in the provided context",
        "is not fully described in the provided context",
        "is not explicitly stated here",
        "is not clearly specified",
        "the context does not specify the rate",
        "the context does not fully describe the rate",
        "I cannot answer that part of your question",
        "I cannot fully answer your question",
        "there is no specific figure",
        "it is unclear from the context",
        "is not covered by the provided excerpts",
        "is not given in the context",
    ],
)
def test_hedges_in_matches_reworded_concessions(wording):
    assert hedges_in(f"The 2030 share {wording} [DOC-A#0000]."), wording


@pytest.mark.parametrize(
    "answer",
    [
        # Must NOT fire: ordinary answers that merely contain "not" or a listed verb.
        "The share is 29% [DOC-A#0000].",
        "Suppliers must ensure the fuel is not blended beyond the stated share [DOC-A#0000].",
        "The rate specified in Annex I is 0,7% [DOC-A#0000].",
        "Food and feed crops are excluded, as described in Annex IX [DOC-A#0000].",
        "This obligation is clear and applies from 2030 [DOC-A#0000].",
    ],
)
def test_hedges_in_does_not_overmatch(answer):
    assert hedges_in(answer) == [], answer


def test_hedges_in_dedupes_and_reports_matched_text():
    found = hedges_in("not specified here, and still not specified there, and not described")
    assert found == ["not specified", "not described"]


def test_declined_passes_when_no_hedge():
    passed, _ = check_declined_despite_retrieval(trace())
    assert passed


def test_declined_does_not_flag_below_threshold():
    t = trace(
        answer="Not specified in the provided context.",
        retrieved=[{"chunk_id": "DOC-A#0000", "document_id": "DOC-A", "score": 0.5}],
    )
    passed, reason = check_declined_despite_retrieval(t)
    assert passed
    assert "below the 5-chunk flag threshold" in reason


def test_declined_is_case_insensitive_and_whitespace_tolerant():
    t = trace(answer="The figure is   NOT  SPECIFIED   here.")
    # Normalisation collapses runs of whitespace, so the phrase is found despite the spacing.
    passed, _ = check_declined_despite_retrieval(t)
    assert not passed


def test_declined_ignores_the_fixed_refusal_sentence():
    """Documented scope limit: a plain refusal is not a hedge, so q11's shape passes."""
    t = trace(answer=REFUSAL, citations=[], refused=True)
    passed, reason = check_declined_despite_retrieval(t)
    assert passed
    assert "no hedge phrase" in reason


def test_declined_handles_curly_apostrophes():
    """F2 showed the model mixes ' and ' — normalisation must not break phrase matching."""
    t = trace(answer="The context doesn’t help; the rate is not specified.")
    passed, _ = check_declined_despite_retrieval(t)
    assert not passed


# ── declined() helper ─────────────────────────────────────────────────
def test_declined_detects_the_fixed_refusal_sentence():
    gave_up, how = declined(trace(answer=REFUSAL, citations=[], refused=True))
    assert gave_up and "fixed refusal sentence" in how


def test_declined_detects_refused_flag_without_the_sentence():
    gave_up, how = declined(trace(answer="Something else entirely.", refused=True))
    assert gave_up and how == "refused=True"


def test_declined_detects_a_hedge():
    gave_up, how = declined(trace(answer="The rate is not specified [DOC-A#0000]."))
    assert gave_up and "hedged" in how


def test_declined_false_on_a_plain_answer():
    gave_up, how = declined(trace())
    assert not gave_up and how == "answered"


# ── check 5: over_refusal (needs the human label) ─────────────────────
def test_over_refusal_fails_on_yes_plus_refusal():
    """The q11 shape: answer was retrievable, model returned the fixed refusal."""
    t = trace(answer=REFUSAL, citations=[], refused=True, answerable="Yes")
    passed, reason = check_over_refusal(t)
    assert not passed
    assert "over-refusal" in reason and "fixed refusal sentence" in reason


def test_over_refusal_fails_on_yes_plus_hedge():
    t = trace(answer="The 2030 share is not detailed here [DOC-A#0000].", answerable="Yes")
    passed, reason = check_over_refusal(t)
    assert not passed
    assert "hedged" in reason


def test_over_refusal_passes_on_yes_plus_answer():
    passed, reason = check_over_refusal(trace(answerable="Yes"))
    assert passed and reason == "answerable=Yes and answered"


def test_over_refusal_passes_on_no_plus_refusal():
    """The q16/q17/q18 shape: refusing is correct when the corpus lacks the fact."""
    t = trace(answer=REFUSAL, citations=[], refused=True, answerable="No")
    passed, reason = check_over_refusal(t)
    assert passed and "declining is correct" in reason


def test_over_refusal_passes_on_partly():
    t = trace(answer=REFUSAL, citations=[], refused=True, answerable="Partly")
    passed, reason = check_over_refusal(t)
    assert passed and "not scored" in reason


def test_over_refusal_skips_unlabelled():
    t = trace(answer=REFUSAL, citations=[], refused=True)
    passed, reason = check_over_refusal(t)
    assert passed and "not evaluated" in reason


def test_over_refusal_skips_unrecognised_value():
    passed, reason = check_over_refusal(trace(answerable="maybe"))
    assert passed and "unrecognised" in reason


# ── over_refusal_rate() ───────────────────────────────────────────────
def test_rate_is_none_when_nothing_is_labelled():
    r = over_refusal_rate([trace(id="a"), trace(id="b")])
    assert r["rate"] is None
    assert r["traces_labelled"] == 0 and r["traces_unlabelled"] == 2


def test_rate_counts_only_answerable_yes():
    traces = [
        trace(id="a", answerable="Yes", answer=REFUSAL, citations=[], refused=True),  # wrong
        trace(id="b", answerable="Yes"),                                              # fine
        trace(id="c", answerable="No", answer=REFUSAL, citations=[], refused=True),   # correct
        trace(id="d"),                                                                # unlabelled
    ]
    r = over_refusal_rate(traces)
    assert r["answerable_yes"] == 2
    assert r["wrongly_refused"] == 1
    assert r["wrongly_refused_ids"] == ["a"]
    assert r["rate"] == 0.5
    assert r["traces_labelled"] == 3 and r["traces_unlabelled"] == 1


def test_rate_is_zero_not_none_when_all_answerable_are_answered():
    """0.0 and None are different claims: 'none wrong' vs 'nothing measured'."""
    r = over_refusal_rate([trace(id="a", answerable="Yes")])
    assert r["rate"] == 0.0


# ── registry ──────────────────────────────────────────────────────────
def test_run_all_returns_every_check():
    results = run_all(trace())
    assert set(results) == {
        "citations_were_retrieved",
        "refusal_consistency",
        "no_uncited_numbers",
        "declined_despite_retrieval",
        "over_refusal",
    }
    assert all(isinstance(v, tuple) and len(v) == 2 for v in results.values())


def test_checks_tolerate_missing_fields():
    """A malformed trace must not raise — an eval harness that crashes reports nothing."""
    for name, (passed, reason) in run_all({"id": "empty"}).items():
        assert isinstance(passed, bool), name
        assert reason, name
