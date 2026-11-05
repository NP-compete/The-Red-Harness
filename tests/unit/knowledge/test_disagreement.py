"""Noticing when two sources say different things about the same question."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.knowledge.disagreement import Finding, find_disagreement

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def finding(source: str, answer: str, **kwargs) -> Finding:
    defaults = {
        "updated_at": NOW - timedelta(days=30),
        "authority": "reference",
    }
    defaults.update(kwargs)
    return Finding(source=source, answer=answer, **defaults)


def test_sources_that_agree_raise_nothing():
    result = find_disagreement([finding("a", "500"), finding("b", "500")], now=NOW)
    assert result.disagree is False


def test_sources_that_differ_are_reported():
    result = find_disagreement([finding("a", "500"), finding("b", "1000")], now=NOW)
    assert result.disagree is True


def test_the_differing_answers_are_listed():
    result = find_disagreement([finding("a", "500"), finding("b", "1000")], now=NOW)
    assert set(result.answers) == {"500", "1000"}


def test_each_answer_says_which_sources_gave_it():
    result = find_disagreement(
        [finding("a", "500"), finding("b", "500"), finding("c", "1000")], now=NOW
    )
    assert result.by_answer["500"] == ("a", "b")


def test_the_most_recently_updated_source_is_preferred():
    stale = finding("old", "500", updated_at=NOW - timedelta(days=400))
    fresh = finding("new", "1000", updated_at=NOW - timedelta(days=1))
    assert find_disagreement([stale, fresh], now=NOW).preferred == "1000"


def test_an_authoritative_source_outranks_a_more_recent_one():
    notes = finding("notes", "500", updated_at=NOW, authority="note")
    policy = finding(
        "policy", "1000", updated_at=NOW - timedelta(days=200), authority="policy"
    )
    assert find_disagreement([notes, policy], now=NOW).preferred == "1000"


def test_the_reason_for_preferring_one_is_given():
    notes = finding("notes", "500", updated_at=NOW, authority="note")
    policy = finding(
        "policy", "1000", updated_at=NOW - timedelta(days=200), authority="policy"
    )
    assert "policy" in find_disagreement([notes, policy], now=NOW).reason


def test_no_answer_is_preferred_when_nothing_distinguishes_them():
    first = finding("a", "500")
    second = finding("b", "1000")
    assert find_disagreement([first, second], now=NOW).preferred == ""


def test_an_undecidable_disagreement_says_both_should_be_shown():
    first = finding("a", "500")
    second = finding("b", "1000")
    assert find_disagreement([first, second], now=NOW).show_both is True


def test_a_decided_disagreement_still_mentions_the_other_answer():
    notes = finding("notes", "500", authority="note")
    policy = finding("policy", "1000", authority="policy")
    assert find_disagreement([notes, policy], now=NOW).show_both is True


def test_agreement_does_not_ask_for_both_to_be_shown():
    result = find_disagreement([finding("a", "500"), finding("b", "500")], now=NOW)
    assert result.show_both is False


def test_answers_differing_only_by_spacing_are_the_same_answer():
    result = find_disagreement([finding("a", " 500 "), finding("b", "500")], now=NOW)
    assert result.disagree is False


def test_answers_differing_only_by_case_are_the_same_answer():
    result = find_disagreement([finding("a", "Yes"), finding("b", "yes")], now=NOW)
    assert result.disagree is False


def test_a_single_source_cannot_disagree_with_itself():
    assert find_disagreement([finding("a", "500")], now=NOW).disagree is False


def test_no_sources_at_all_is_refused():
    with pytest.raises(ValueError):
        find_disagreement([], now=NOW)


def test_a_finding_without_a_source_is_refused():
    with pytest.raises(ValueError):
        finding(" ", "500")


def test_a_finding_with_no_answer_is_refused():
    with pytest.raises(ValueError):
        finding("a", "   ")
