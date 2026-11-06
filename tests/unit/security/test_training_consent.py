"""Whether a conversation may be kept and studied to improve the system."""

from __future__ import annotations

import pytest

from agent.src.security.training_consent import (
    Conversation,
    Refusal,
    Settings,
    may_use,
)


def settings(**kwargs) -> Settings:
    defaults = {"org_allows": True, "user_opted_in": True, "requires_opt_in": True}
    defaults.update(kwargs)
    return Settings(**defaults)


def conversation(**kwargs) -> Conversation:
    defaults = {
        "thread": "t1",
        "contains_personal_data": False,
        "on_legal_hold": False,
        "shared_externally": False,
        "classification": "internal",
    }
    defaults.update(kwargs)
    return Conversation(**defaults)


def test_an_opted_in_conversation_may_be_used():
    assert may_use(conversation(), settings()).permitted is True


def test_nothing_may_be_used_when_the_organisation_says_no():
    decision = may_use(conversation(), settings(org_allows=False))
    assert decision.refusal is Refusal.ORG_FORBIDS


def test_the_organisation_outranks_an_individual_opt_in():
    decision = may_use(conversation(), settings(org_allows=False, user_opted_in=True))
    assert decision.permitted is False


def test_a_conversation_without_an_opt_in_may_not_be_used():
    decision = may_use(conversation(), settings(user_opted_in=False))
    assert decision.refusal is Refusal.NO_CONSENT


def test_consent_is_assumed_off_rather_than_on():
    decision = may_use(conversation(), Settings(org_allows=True, user_opted_in=False))
    assert decision.permitted is False


def test_an_organisation_may_decide_consent_is_not_needed():
    relaxed = settings(user_opted_in=False, requires_opt_in=False)
    assert may_use(conversation(), relaxed).permitted is True


def test_a_conversation_under_legal_hold_is_never_used():
    decision = may_use(conversation(on_legal_hold=True), settings())
    assert decision.refusal is Refusal.LEGAL_HOLD


def test_a_legal_hold_outranks_every_permission():
    relaxed = settings(requires_opt_in=False)
    assert may_use(conversation(on_legal_hold=True), relaxed).permitted is False


def test_a_conversation_holding_personal_data_is_not_used_as_it_stands():
    decision = may_use(conversation(contains_personal_data=True), settings())
    assert decision.permitted is False


def test_personal_data_can_be_removed_first():
    decision = may_use(conversation(contains_personal_data=True), settings())
    assert decision.refusal is Refusal.NEEDS_SCRUBBING


def test_a_conversation_needing_scrubbing_says_what_would_make_it_usable():
    decision = may_use(conversation(contains_personal_data=True), settings())
    assert "removed" in decision.reason


def test_a_scrubbed_conversation_may_be_used():
    decision = may_use(
        conversation(contains_personal_data=True), settings(), scrubbed=True
    )
    assert decision.permitted is True


def test_scrubbing_does_not_rescue_a_conversation_under_hold():
    decision = may_use(conversation(on_legal_hold=True), settings(), scrubbed=True)
    assert decision.permitted is False


def test_a_restricted_conversation_is_never_used():
    decision = may_use(conversation(classification="restricted"), settings())
    assert decision.refusal is Refusal.CLASSIFICATION


def test_a_conversation_shared_outside_the_organisation_is_not_used():
    decision = may_use(conversation(shared_externally=True), settings())
    assert decision.refusal is Refusal.SHARED_EXTERNALLY


def test_a_permitted_decision_carries_no_refusal():
    assert may_use(conversation(), settings()).refusal is None


def test_an_unknown_classification_is_refused_outright():
    with pytest.raises(ValueError):
        conversation(classification="whatever")


def test_a_conversation_without_a_thread_is_refused():
    with pytest.raises(ValueError):
        conversation(thread=" ")
