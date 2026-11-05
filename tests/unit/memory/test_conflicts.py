"""What to do when something newly learned contradicts what is remembered."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.memory.conflicts import Memory, Resolution, reconcile

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def memory(**kwargs) -> Memory:
    defaults = {
        "key": "preferred-format",
        "value": "markdown",
        "learned_at": NOW - timedelta(days=30),
        "source": "stated",
        "confidence": 0.9,
    }
    defaults.update(kwargs)
    return Memory(**defaults)


def test_a_new_fact_about_something_unknown_is_simply_kept():
    assert reconcile(memory(), existing=None, now=NOW).resolution is Resolution.ADDED


def test_the_same_fact_again_changes_nothing():
    assert (
        reconcile(memory(), existing=memory(), now=NOW).resolution
        is Resolution.UNCHANGED
    )


def test_repeating_a_fact_does_not_move_the_date_it_was_learned():
    again = memory(learned_at=NOW)
    result = reconcile(again, existing=memory(), now=NOW)
    assert result.kept.learned_at == memory().learned_at


def test_repeating_a_fact_strengthens_it():
    again = memory(learned_at=NOW)
    result = reconcile(again, existing=memory(confidence=0.6), now=NOW)
    assert result.kept.confidence > 0.6


def test_confidence_never_exceeds_certainty():
    again = memory(confidence=1.0, learned_at=NOW)
    result = reconcile(again, existing=memory(confidence=1.0), now=NOW)
    assert result.kept.confidence == 1.0


def test_a_contradicting_fact_the_person_stated_wins():
    newer = memory(value="plain text", learned_at=NOW, source="stated")
    result = reconcile(newer, existing=memory(), now=NOW)
    assert result.resolution is Resolution.SUPERSEDED


def test_a_superseded_memory_keeps_the_new_value():
    newer = memory(value="plain text", learned_at=NOW)
    assert reconcile(newer, existing=memory(), now=NOW).kept.value == "plain text"


def test_the_old_value_is_remembered_as_what_it_replaced():
    newer = memory(value="plain text", learned_at=NOW)
    assert reconcile(newer, existing=memory(), now=NOW).replaced == "markdown"


def test_something_merely_inferred_does_not_overturn_what_was_stated():
    guess = memory(
        value="plain text", learned_at=NOW, source="inferred", confidence=0.6
    )
    assert (
        reconcile(guess, existing=memory(), now=NOW).resolution
        is Resolution.KEPT_EXISTING
    )


def test_an_inferred_fact_can_overturn_another_inferred_fact():
    old = memory(source="inferred", confidence=0.5)
    guess = memory(
        value="plain text", learned_at=NOW, source="inferred", confidence=0.8
    )
    assert reconcile(guess, existing=old, now=NOW).resolution is Resolution.SUPERSEDED


def test_a_weaker_guess_does_not_overturn_a_stronger_one():
    old = memory(source="inferred", confidence=0.8)
    guess = memory(
        value="plain text", learned_at=NOW, source="inferred", confidence=0.5
    )
    assert (
        reconcile(guess, existing=old, now=NOW).resolution is Resolution.KEPT_EXISTING
    )


def test_a_stated_fact_overturns_an_inferred_one_whatever_the_confidence():
    old = memory(source="inferred", confidence=0.99)
    stated = memory(value="plain text", learned_at=NOW, source="stated", confidence=0.5)
    assert reconcile(stated, existing=old, now=NOW).resolution is Resolution.SUPERSEDED


def test_a_conflict_is_worth_mentioning_to_the_person():
    newer = memory(value="plain text", learned_at=NOW)
    assert reconcile(newer, existing=memory(), now=NOW).worth_mentioning is True


def test_an_unremarkable_addition_is_not_worth_mentioning():
    assert reconcile(memory(), existing=None, now=NOW).worth_mentioning is False


def test_a_very_old_memory_is_overturned_more_readily():
    ancient = memory(source="stated", learned_at=NOW - timedelta(days=400))
    guess = memory(
        value="plain text", learned_at=NOW, source="inferred", confidence=0.6
    )
    assert (
        reconcile(guess, existing=ancient, now=NOW).resolution is Resolution.SUPERSEDED
    )


def test_a_memory_about_a_different_thing_is_not_a_conflict():
    other = memory(key="preferred-language", value="english")
    with pytest.raises(ValueError):
        reconcile(other, existing=memory(), now=NOW)


def test_a_memory_without_a_key_is_refused():
    with pytest.raises(ValueError):
        memory(key=" ")


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_an_impossible_confidence_is_refused(confidence):
    with pytest.raises(ValueError):
        memory(confidence=confidence)
