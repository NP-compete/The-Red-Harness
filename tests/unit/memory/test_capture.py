"""Deciding what from a conversation is worth keeping."""

from __future__ import annotations

import pytest

from agent.src.memory.capture import Candidate, Decision, decide_capture


def candidate(**kwargs) -> Candidate:
    defaults = {
        "text": "I prefer metric units in every report.",
        "durable": True,
        "about_the_person": True,
        "sensitive": False,
        "already_known": False,
        "stated_by_person": True,
        "asked_to_remember": False,
        "asked_to_forget": False,
    }
    defaults.update(kwargs)
    return Candidate(**defaults)


def test_a_lasting_preference_is_kept():
    assert decide_capture(candidate()).decision is Decision.KEEP


def test_the_text_comes_through_unchanged():
    assert decide_capture(candidate()).text == "I prefer metric units in every report."


def test_something_true_only_today_is_not_kept():
    passing = candidate(text="Use Berlin time for this one meeting.", durable=False)
    assert decide_capture(passing).decision is Decision.DISCARD


def test_something_already_known_is_not_written_twice():
    assert decide_capture(candidate(already_known=True)).decision is Decision.DISCARD


def test_a_duplicate_says_so():
    assert "already" in decide_capture(candidate(already_known=True)).reason


def test_an_explicit_request_to_remember_is_honoured_even_when_passing():
    asked = candidate(durable=False, asked_to_remember=True)
    assert decide_capture(asked).decision is Decision.KEEP


def test_an_explicit_request_outranks_the_agent_s_own_judgement():
    asked = candidate(durable=False, about_the_person=False, asked_to_remember=True)
    assert decide_capture(asked).decision is Decision.KEEP


def test_an_explicit_request_to_forget_overrides_everything():
    asked = candidate(asked_to_remember=True, asked_to_forget=True)
    assert decide_capture(asked).decision is Decision.DISCARD


def test_sensitive_material_is_never_written_on_the_agent_s_own_initiative():
    assert decide_capture(candidate(sensitive=True)).decision is Decision.ASK


def test_sensitive_material_the_person_asked_for_is_kept():
    asked = candidate(sensitive=True, asked_to_remember=True)
    assert decide_capture(asked).decision is Decision.KEEP


def test_asking_explains_why_it_is_asking():
    assert decide_capture(candidate(sensitive=True)).reason


def test_something_the_agent_inferred_rather_than_heard_is_not_kept_silently():
    guessed = candidate(stated_by_person=False)
    assert decide_capture(guessed).decision is Decision.ASK


def test_an_inference_the_person_confirmed_is_kept():
    confirmed = candidate(stated_by_person=False, asked_to_remember=True)
    assert decide_capture(confirmed).decision is Decision.KEEP


def test_something_about_the_work_rather_than_the_person_is_still_kept():
    project = candidate(
        text="The quarterly report is due on the fifth.", about_the_person=False
    )
    assert decide_capture(project).decision is Decision.KEEP


def test_a_kept_memory_needs_no_confirmation():
    assert decide_capture(candidate()).needs_confirmation is False


def test_an_asked_memory_needs_confirmation():
    assert decide_capture(candidate(sensitive=True)).needs_confirmation is True


def test_empty_text_is_refused():
    with pytest.raises(ValueError):
        candidate(text="   ")
