"""Unit tests for the Watchbird write gate and whats_new_vs_before.

No database, no OpenAI, no FastAPI client: gate_reason() and whats_new_vs_before() are pure
functions on mappings, which is the point of keeping them separate from remember().

The six gate cases below are the contract from the assignment: persist only when ping is true,
citations are non-empty, confidence >= 0.6 and stage is a valid enum value. Four accept, two
reject — and the two rejections are the ones that matter, because a verdict that reaches the
store becomes history that every later run treats as established fact.

Each assertion is keyed on the *outcome* (stored or not) and on a structural feature of the
reason, never on the reason's exact wording — rewording a log line must not fail a test, but
silently accepting an ungrounded verdict must.
"""

from datetime import datetime, timezone

import pytest

from server.memory import (
    FIRST_TIME,
    GATE_MIN_CONFIDENCE,
    NOT_TRACKED,
    STAGES,
    canonical_fuels,
    display_fuels,
    gate_reason,
    normalise_fuels,
    story_key,
    whats_new_vs_before,
)


def verdict(**overrides):
    """A verdict that passes every gate condition, so each test changes exactly one thing."""
    base = {
        "ping": True,
        "instrument": "ReFuelEU Aviation",
        "jurisdiction": "EU",
        "eu_channel": "mandate",
        "fuels": ["SAF"],
        "stage": "in_force",
        "what_happened": "The Commission confirmed the 2030 SAF blending share.",
        "why_it_matters": "It sets the aviation blending obligation.",
        "citations": ["refueleu#0003"],
        "confidence": 0.82,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# The six write-gate cases: 4 accepted, 2 rejected
# ---------------------------------------------------------------------------

def test_case_1_fully_grounded_high_confidence_ping_is_stored():
    assert gate_reason(verdict()) is None


def test_case_2_confidence_exactly_at_the_threshold_is_stored():
    """0.6 is the documented boundary and must be inclusive, not off by one."""
    assert gate_reason(verdict(confidence=GATE_MIN_CONFIDENCE)) is None


def test_case_3_provisional_duty_on_a_non_eu_jurisdiction_is_stored():
    """A Chinese measure reaching the EU market is in scope, not a foreign-news reject."""
    allowed = verdict(
        instrument="EU anti-dumping duty on Chinese biodiesel",
        jurisdiction="China",
        eu_channel="import_duty",
        fuels=["biodiesel", "HVO"],
        stage="provisional",
        citations=["duties#0001", "duties#0002"],
        confidence=0.71,
    )
    assert gate_reason(allowed) is None


def test_case_4_every_valid_stage_passes_the_gate():
    """The gate must accept all six stages, or stage-change detection loses states."""
    for stage in STAGES:
        assert gate_reason(verdict(stage=stage)) is None, stage


def test_case_5_rejected_no_citations_means_the_verdict_is_not_grounded():
    """An ungrounded verdict must never become a remembered fact (F2/F7).

    This is the rejection that matters most: the model can produce a perfectly well-formed,
    confident ping with no evidence behind it, and a schema check would pass it.
    """
    reason = gate_reason(verdict(citations=[]))
    assert reason is not None
    assert "citation" in reason.lower()


def test_case_6_rejected_confidence_below_the_threshold_is_a_guess():
    reason = gate_reason(verdict(confidence=0.59))
    assert reason is not None
    assert "confidence" in reason.lower()


# ---------------------------------------------------------------------------
# The remaining gate conditions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "overrides, expect_in_reason",
    [
        ({"ping": False}, "ping"),
        ({"stage": "in force"}, "stage"),       # prose instead of the enum value (F4)
        ({"stage": "enacted"}, "stage"),        # invented stage
        ({"stage": None}, "stage"),
        ({"confidence": None}, "confidence"),
        ({"confidence": "high"}, "confidence"),  # not a number
        ({"instrument": None}, "instrument"),
        ({"instrument": "   "}, "instrument"),
    ],
)
def test_other_rejections(overrides, expect_in_reason):
    reason = gate_reason(verdict(**overrides))
    assert reason is not None, overrides
    assert expect_in_reason in reason.lower()


# ---------------------------------------------------------------------------
# Story identity
# ---------------------------------------------------------------------------

def test_story_key_is_stable_across_fuel_order_case_and_spacing():
    a = story_key("ReFuelEU Aviation", "EU", ["SAF", "HVO"], "mandate")
    b = story_key("refueleu  aviation", "eu", ["  hvo ", "saf"], "mandate")
    assert a == b != ""


def test_story_key_separates_different_channels_for_the_same_instrument():
    target = story_key("RED III", "EU", ["biodiesel"], "target")
    duty = story_key("RED III", "EU", ["biodiesel"], "import_duty")
    assert target != duty


def test_story_key_is_empty_without_an_instrument():
    assert story_key(None, "EU", ["SAF"], "mandate") == ""


def test_unknown_channel_is_coerced_to_other_rather_than_splitting_the_story():
    assert story_key("RED III", "EU", ["SAF"], "something new").endswith("|other")


def test_normalise_fuels_dedupes_and_sorts():
    assert normalise_fuels([" SAF ", "saf", "HVO", ""]) == ["hvo", "saf"]


# ---------------------------------------------------------------------------
# whats_new_vs_before — the four cases from the assignment
# ---------------------------------------------------------------------------

def previous_row(**overrides):
    base = {
        "story_key": "refueleu-aviation|eu|saf|mandate",
        "instrument": "ReFuelEU Aviation",
        "jurisdiction": "EU",
        "fuels": ["saf"],
        "latest_stage": "proposed",
        "last_seen": datetime(2026, 10, 20, 9, 30, tzinfo=timezone.utc),
        "ping_count": 1,
    }
    base.update(overrides)
    return base


def test_no_match_says_first_time():
    assert whats_new_vs_before(None, verdict()) == FIRST_TIME


def test_no_match_and_no_instrument_says_not_tracked():
    assert whats_new_vs_before(None, verdict(instrument=None)) == NOT_TRACKED


def test_same_stage_says_seen_before_with_the_date():
    text = whats_new_vs_before(previous_row(latest_stage="in_force"), verdict(stage="in_force"))
    assert "2026-10-20" in text
    assert "no stage change" in text


def test_new_stage_names_both_stages_and_the_date():
    text = whats_new_vs_before(previous_row(latest_stage="proposed"), verdict(stage="in_force"))
    assert "proposed" in text and "in_force" in text
    assert "2026-10-20" in text


def test_new_fuel_is_named_as_an_addition():
    text = whats_new_vs_before(previous_row(fuels=["saf"]), verdict(fuels=["SAF", "HVO"]))
    assert "HVO" in text


def test_new_jurisdiction_is_named_as_an_addition():
    text = whats_new_vs_before(previous_row(jurisdiction="EU"), verdict(jurisdiction="Indonesia"))
    assert "Indonesia" in text


def test_a_stage_change_and_a_new_fuel_are_both_reported():
    text = whats_new_vs_before(
        previous_row(latest_stage="proposed", fuels=["saf"]),
        verdict(stage="in_force", fuels=["SAF", "HVO"]),
    )
    assert "in_force" in text and "HVO" in text


# ---------------------------------------------------------------------------
# Canonical fuel normalisation
# ---------------------------------------------------------------------------

def test_the_regression_from_the_first_recall_run_is_closed():
    """The exact pair that made the exact key miss on 2026-10-27.

    Item 1 returned ["SAF", "synthetic aviation fuel"], item 2 returned ["SAF"], the keys
    differed, and recall fell through to the embedding at 0.8547 - four thousandths above an
    unvalidated threshold. These two must now produce one key.
    """
    first = story_key("ReFuelEU Aviation", "EU", ["SAF", "synthetic aviation fuel"], "mandate")
    second = story_key("ReFuelEU Aviation", "EU", ["SAF"], "mandate")
    assert first == second != ""


@pytest.mark.parametrize(
    "names",
    [
        ["synthetic aviation fuel", "e-SAF", "RFNBO-derived jet", "power-to-liquid jet",
         "e-kerosene", "SAF"],
        ["HVO", "hydrotreated vegetable oil"],
        ["FAME", "biodiesel"],
    ],
)
def test_each_group_collapses_to_exactly_one_token(names):
    assert len(canonical_fuels(names)) == 1


def test_the_three_groups_stay_distinct_from_each_other():
    assert canonical_fuels(["SAF"]) != canonical_fuels(["HVO"]) != canonical_fuels(["FAME"])
    assert len(canonical_fuels(["SAF", "HVO", "FAME"])) == 3


@pytest.mark.parametrize(
    "written",
    ["e-SAF", "E-SAF", "e SAF", "eSAF", "e-SAFs", "  e-saf  "],
)
def test_lookup_survives_case_hyphens_spacing_and_plurals(written):
    assert canonical_fuels([written]) == ["saf"]


def test_an_unmapped_fuel_keeps_its_own_identity_rather_than_being_dropped():
    assert canonical_fuels(["hydrogen"]) == ["hydrogen"]
    assert canonical_fuels(["SAF", "hydrogen"]) == ["hydrogen", "saf"]


def test_display_fuels_keeps_the_classifiers_own_words():
    assert display_fuels([" SAF ", "synthetic aviation fuel", "saf"]) == [
        "SAF", "synthetic aviation fuel",
    ]


def test_story_key_ignores_fuel_granularity_but_not_a_different_fuel():
    saf_only = story_key("RED III", "EU", ["SAF"], "target")
    saf_plus_synthetic = story_key("RED III", "EU", ["SAF", "e-SAF"], "target")
    saf_plus_hvo = story_key("RED III", "EU", ["SAF", "HVO"], "target")
    assert saf_only == saf_plus_synthetic
    assert saf_only != saf_plus_hvo


def test_renaming_a_fuel_is_not_reported_as_an_addition():
    text = whats_new_vs_before(
        previous_row(fuels=["SAF"]), verdict(fuels=["synthetic aviation fuel"])
    )
    assert "now also covers" not in text.lower()


def test_a_genuinely_new_fuel_is_still_reported_in_the_classifiers_words():
    text = whats_new_vs_before(previous_row(fuels=["SAF"]), verdict(fuels=["SAF", "HVO"]))
    assert "HVO" in text


def test_the_confidence_rejection_message_does_not_contradict_itself():
    """A value just below the threshold must not be printed as the threshold.

    `:.2f` rendered 0.5999 as "confidence 0.60 is below 0.6" - a rejection whose own text says
    the value met the bar it was rejected for. The gate was right; only the message lied.
    """
    reason = gate_reason(verdict(confidence=0.5999))
    assert reason is not None
    assert "0.60 is below 0.6" not in reason
    assert "0.5999" in reason
