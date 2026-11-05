"""E17. A chooser whose options send the same request is withheld."""

from __future__ import annotations

import pytest

from agent.src.agent.reasoning_profiles import (
    Profile,
    effort_reaches_the_model,
    worth_offering,
)

ONE_MODEL = {
    "tiers": [
        {"name": "fast", "model": "gemini-3.8-flash"},
        {"name": "deep", "model": "gemini-3.8-flash"},
    ],
    "profiles": [
        {"name": "fast", "tier": "fast", "effort": "low"},
        {"name": "accurate", "tier": "deep", "effort": "high"},
    ],
}

TWO_MODELS = {
    "enabled": True,
    "tiers": [
        {"name": "fast", "model": "gemini-3.8-flash"},
        {"name": "deep", "model": "gemini-3.8-pro"},
    ],
    "profiles": [
        {"name": "fast", "tier": "fast", "effort": "low"},
        {"name": "accurate", "tier": "deep", "effort": "high"},
    ],
}


@pytest.fixture
def no_override(monkeypatch):
    from agent.src.settings import settings

    monkeypatch.setattr(settings, "MODEL_OVERRIDE", None)
    monkeypatch.setattr(settings, "VLLM_BASE_URL", None)
    monkeypatch.setattr(
        "agent.src.agent.config.agent_config.get_orchestrator_config",
        lambda: {"model": "gemini-3.8-flash"},
    )


@pytest.fixture
def pointed_at_a_stub(monkeypatch):
    from agent.src.settings import settings

    monkeypatch.setattr(settings, "MODEL_OVERRIDE", "mock-model")
    monkeypatch.setattr(settings, "VLLM_BASE_URL", "http://127.0.0.1:5004/v1")
    monkeypatch.setattr(
        "agent.src.agent.config.agent_config.get_orchestrator_config",
        lambda: {"model": "gemini-3.8-flash"},
    )


class TestWhereEffortLands:
    def test_a_gemini_model_takes_a_reasoning_budget(self, no_override):
        assert effort_reaches_the_model("gemini-3.8-flash")

    def test_an_openai_compatible_endpoint_drops_it(self, no_override):
        assert not effort_reaches_the_model("/data/some-local-model")

    def test_an_override_puts_every_model_behind_a_stub(self, pointed_at_a_stub):
        """However the tiers are named."""
        assert not effort_reaches_the_model("gemini-3.8-flash")


class TestWhatIsOffered:
    def test_efforts_alone_separate_profiles_on_gemini(self, no_override):
        assert [p.name for p in worth_offering(ONE_MODEL)] == ["fast", "accurate"]

    def test_efforts_alone_are_not_enough_behind_a_stub(self, pointed_at_a_stub):
        """Somebody picks "accurate" and waits, believing something"""
        assert worth_offering(ONE_MODEL) == []

    def test_different_models_are_offered_whatever_the_provider(
        self, pointed_at_a_stub
    ):
        """The request differs on the model name alone, so the"""
        assert [p.name for p in worth_offering(TWO_MODELS)] == ["fast", "accurate"]

    def test_nothing_declared_offers_nothing(self, no_override):
        assert worth_offering({"tiers": [], "profiles": []}) == []

    def test_with_routing_off_it_asks_about_the_agents_own_model(self, no_override):
        """A profile carries no model with routing off, and asking"""
        from agent.src.agent.reasoning_profiles import _model_in_use, profiles_from

        assert _model_in_use(profiles_from(ONE_MODEL)) == "gemini-3.8-flash"


class TestTheProfileItself:
    def test_a_profile_still_records_what_it_asks_for(self):
        """Withholding the chooser does not change the profile: a"""
        one = Profile(
            name="accurate",
            tier="deep",
            model="gemini-3.8-flash",
            effort="high",
            budget_multiplier=1.0,
        )
        assert (one.effort, one.tier) == ("high", "deep")
