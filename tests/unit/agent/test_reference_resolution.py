"""Working out what a follow-up question is pointing at."""

from __future__ import annotations

import pytest

from agent.src.agent.reference_resolution import Mention, resolve_reference


def mention(**kwargs) -> Mention:
    defaults = {
        "entity": "report-7",
        "kind": "report",
        "turns_ago": 1,
        "was_the_subject": True,
    }
    defaults.update(kwargs)
    return Mention(**defaults)


def test_a_question_naming_nothing_points_at_the_last_subject():
    resolved = resolve_reference("send it to finance", mentions=[mention()])
    assert resolved.entity == "report-7"


def test_a_question_that_names_its_subject_needs_no_resolving():
    resolved = resolve_reference("send report-7 to finance", mentions=[mention()])
    assert resolved.entity is None


def test_naming_the_subject_is_reported_as_nothing_to_resolve():
    resolved = resolve_reference("send report-7 to finance", mentions=[mention()])
    assert resolved.resolved is False


def test_the_most_recent_subject_wins_over_an_older_one():
    older = mention(entity="report-3", turns_ago=4)
    recent = mention(entity="report-9", turns_ago=1)
    resolved = resolve_reference("send it", mentions=[older, recent])
    assert resolved.entity == "report-9"


def test_something_that_was_the_subject_beats_something_merely_mentioned():
    aside = mention(entity="report-3", turns_ago=1, was_the_subject=False)
    subject = mention(entity="report-9", turns_ago=2, was_the_subject=True)
    resolved = resolve_reference("send it", mentions=[aside, subject])
    assert resolved.entity == "report-9"


def test_a_reference_to_a_kind_picks_the_last_of_that_kind():
    other = mention(entity="invoice-2", kind="invoice", turns_ago=1)
    report = mention(entity="report-7", kind="report", turns_ago=3)
    resolved = resolve_reference("send that report", mentions=[other, report])
    assert resolved.entity == "report-7"


def test_a_mention_too_far_back_is_not_reached_for():
    stale = mention(turns_ago=20)
    assert resolve_reference("send it", mentions=[stale]).entity is None


def test_nothing_to_point_at_resolves_to_nothing():
    assert resolve_reference("send it", mentions=[]).entity is None


def test_an_unresolved_reference_is_worth_asking_about():
    assert resolve_reference("send it", mentions=[]).should_ask is True


def test_a_resolved_reference_is_not_asked_about():
    assert resolve_reference("send it", mentions=[mention()]).should_ask is False


def test_a_question_with_no_reference_in_it_is_not_asked_about():
    resolved = resolve_reference("what is the expense limit", mentions=[])
    assert resolved.should_ask is False


def test_two_equally_good_candidates_are_asked_about_rather_than_guessed():
    first = mention(entity="report-7", turns_ago=1)
    second = mention(entity="report-9", turns_ago=1)
    resolved = resolve_reference("send it", mentions=[first, second])
    assert resolved.should_ask is True


def test_an_ambiguous_reference_offers_what_it_was_torn_between():
    first = mention(entity="report-7", turns_ago=1)
    second = mention(entity="report-9", turns_ago=1)
    resolved = resolve_reference("send it", mentions=[first, second])
    assert resolved.candidates == ["report-7", "report-9"]


def test_a_confident_resolution_offers_no_alternatives():
    assert resolve_reference("send it", mentions=[mention()]).candidates == []


def test_an_empty_question_is_refused():
    with pytest.raises(ValueError):
        resolve_reference("   ", mentions=[mention()])


def test_a_mention_from_the_future_is_refused():
    with pytest.raises(ValueError):
        mention(turns_ago=-1)
