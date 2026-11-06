"""Reading material written in a language other than the question."""

from __future__ import annotations

import pytest

from agent.src.knowledge.language_mismatch import Found, Handling, plan_reading


def found(**kwargs) -> Found:
    defaults = {
        "chunk": "c1",
        "language": "en",
        "confidence": 0.9,
        "translatable": True,
    }
    defaults.update(kwargs)
    return Found(**defaults)


def test_material_in_the_asked_language_is_read_as_it_is():
    plan = plan_reading([found()], asked_in="en")
    assert plan[0].handling is Handling.AS_IS


def test_material_in_another_language_is_translated_before_reading():
    plan = plan_reading([found(language="de")], asked_in="en")
    assert plan[0].handling is Handling.TRANSLATE


def test_translated_material_is_still_read():
    plan = plan_reading([found(language="de")], asked_in="en")
    assert [step.chunk for step in plan] == ["c1"]


def test_material_that_cannot_be_translated_is_still_offered_untranslated():
    plan = plan_reading([found(language="de", translatable=False)], asked_in="en")
    assert plan[0].handling is Handling.UNTRANSLATED


def test_a_language_guess_made_with_little_confidence_is_not_acted_on():
    plan = plan_reading([found(language="de", confidence=0.3)], asked_in="en")
    assert plan[0].handling is Handling.AS_IS


def test_an_unconfident_guess_is_reported_as_uncertain():
    plan = plan_reading([found(language="de", confidence=0.3)], asked_in="en")
    assert plan[0].language_uncertain is True


def test_a_confident_guess_is_not_reported_as_uncertain():
    plan = plan_reading([found(language="de")], asked_in="en")
    assert plan[0].language_uncertain is False


def test_the_language_found_is_carried_through():
    plan = plan_reading([found(language="de")], asked_in="en")
    assert plan[0].language == "de"


def test_each_piece_is_handled_on_its_own():
    mixed = [found(chunk="c1"), found(chunk="c2", language="fr")]
    plan = plan_reading(mixed, asked_in="en")
    assert [step.handling for step in plan] == [Handling.AS_IS, Handling.TRANSLATE]


def test_the_order_found_is_the_order_read():
    mixed = [found(chunk="c2", language="fr"), found(chunk="c1")]
    plan = plan_reading(mixed, asked_in="en")
    assert [step.chunk for step in plan] == ["c2", "c1"]


def test_regional_variants_of_the_same_language_are_not_a_mismatch():
    plan = plan_reading([found(language="en-GB")], asked_in="en-US")
    assert plan[0].handling is Handling.AS_IS


def test_finding_nothing_plans_nothing():
    assert plan_reading([], asked_in="en") == []


def test_a_question_with_no_language_is_refused():
    with pytest.raises(ValueError):
        plan_reading([found()], asked_in="  ")


def test_a_confidence_outside_its_range_is_refused():
    with pytest.raises(ValueError):
        found(confidence=1.5)
