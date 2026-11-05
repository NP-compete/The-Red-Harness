"""How plainly an answer should be stated, given what it rests on."""

from __future__ import annotations

import pytest

from agent.src.agent.answer_confidence import Signals, Stance, decide_stance


def signals(**kwargs) -> Signals:
    defaults = {
        "coverage": 1.0,
        "claims_supported": 1.0,
        "sources": 3,
        "sources_disagree": False,
        "oldest_source_days": 10,
        "freshness_matters": False,
        "built_on_untrusted": False,
    }
    defaults.update(kwargs)
    return Signals(**defaults)


def test_a_well_supported_answer_is_stated_plainly():
    assert decide_stance(signals()).stance is Stance.PLAIN


def test_a_plainly_stated_answer_carries_no_hedge():
    assert decide_stance(signals()).hedge == ""


def test_an_answer_covering_only_part_of_the_question_is_hedged():
    partial = signals(coverage=0.5)
    assert decide_stance(partial).stance is Stance.HEDGED


def test_a_partial_answer_says_what_it_missed():
    partial = signals(coverage=0.5)
    assert "part" in decide_stance(partial).hedge


def test_an_answer_whose_claims_are_mostly_unsupported_is_declined():
    unsupported = signals(claims_supported=0.2)
    assert decide_stance(unsupported).stance is Stance.DECLINE


def test_an_answer_resting_on_one_source_is_hedged():
    thin = signals(sources=1)
    assert decide_stance(thin).stance is Stance.HEDGED


def test_an_answer_resting_on_no_sources_is_declined():
    assert decide_stance(signals(sources=0)).stance is Stance.DECLINE


def test_sources_that_disagree_are_surfaced_rather_than_picked_between():
    split = signals(sources_disagree=True)
    assert decide_stance(split).stance is Stance.HEDGED


def test_disagreement_is_named_in_the_hedge():
    split = signals(sources_disagree=True)
    assert "disagree" in decide_stance(split).hedge


def test_old_sources_matter_only_where_recency_matters():
    old = signals(oldest_source_days=900)
    assert decide_stance(old).stance is Stance.PLAIN


def test_old_sources_are_hedged_where_recency_matters():
    old = signals(oldest_source_days=900, freshness_matters=True)
    assert decide_stance(old).stance is Stance.HEDGED


def test_an_answer_built_on_untrusted_material_is_always_hedged():
    tainted = signals(built_on_untrusted=True)
    assert decide_stance(tainted).stance is Stance.HEDGED


def test_a_declined_answer_says_what_would_make_it_answerable():
    declined = decide_stance(signals(sources=0))
    assert declined.what_would_help


def test_an_answer_with_several_problems_names_them_all():
    poor = signals(coverage=0.5, sources=1, sources_disagree=True)
    assert len(decide_stance(poor).concerns) == 3


def test_a_sound_answer_has_no_concerns():
    assert decide_stance(signals()).concerns == []


def test_a_coverage_outside_its_range_is_refused():
    with pytest.raises(ValueError):
        signals(coverage=1.4)


def test_a_negative_source_count_is_refused():
    with pytest.raises(ValueError):
        signals(sources=-1)
