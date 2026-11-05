"""How much the model may reason before it answers."""

from __future__ import annotations

import pytest

from agent.src.agent.llm import _thinking_budget
from agent.src.settings import settings


class TestReasoningIsOffByDefault:
    """Dynamic did not do what its name suggests."""

    def test_the_shipped_default_is_off(self):
        assert settings.THINKING_BUDGET == 0

    def test_zero_is_sent_rather_than_omitted(self, monkeypatch):
        """0 is an instruction — do not reason — and has to reach the"""
        monkeypatch.setattr(settings, "THINKING_BUDGET", 0)
        assert _thinking_budget() == 0


class TestTheModelCanBeGivenTheDecisionBack:
    def test_minus_one_sends_nothing_so_the_model_budgets_itself(self, monkeypatch):
        """`None` means "do not send the field", which is how the SDK"""
        monkeypatch.setattr(settings, "THINKING_BUDGET", -1)
        assert _thinking_budget() is None


class TestTheOverrideStillWorks:
    def test_a_ceiling_can_be_pinned(self, monkeypatch):
        monkeypatch.setattr(settings, "THINKING_BUDGET", 2048)
        assert _thinking_budget() == 2048


class TestItNoLongerGuessesFromTheModelName:
    @pytest.mark.parametrize(
        "model",
        ["gemini-2.5-pro", "gemini-3.8-flash", "claude-sonnet-4", "mock-model"],
    )
    def test_no_model_is_treated_differently(self, model, monkeypatch):
        """The prefix list is gone. Keeping it correct meant editing a"""
        monkeypatch.setattr(settings, "THINKING_BUDGET", -1)
        assert _thinking_budget() is None

    def test_the_prefix_setting_is_gone(self):
        assert not hasattr(settings, "THINKING_MODEL_PREFIXES")
        assert not hasattr(settings, "THINKING_BUDGET_SHARE")
        assert not hasattr(settings, "MIN_THINKING_BUDGET")
