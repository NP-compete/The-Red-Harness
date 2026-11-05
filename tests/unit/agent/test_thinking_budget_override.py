"""A per-run reasoning budget actually reaches the provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.src.agent.llm import create_model
from agent.src.settings import settings


def _built(**over):
    """Build a Gemini model and return the kwargs it was given."""
    seen: dict = {}

    class _Fake:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    with (
        patch("agent.src.agent.llm.ChatGoogleGenerativeAI", _Fake),
        patch(
            "agent.src.agent.llm.get_service_account_credentials",
            return_value=(MagicMock(), "a-project"),
        ),
    ):
        create_model(model_name="gemini-3.8-flash", **over)
    return seen


class TestWhenARunAsksForOne:
    def test_the_budget_it_asked_for_is_what_is_built(self):
        assert _built(thinking_budget=4096)["thinking_budget"] == 4096

    def test_zero_is_a_budget_not_an_absence(self):
        assert _built(thinking_budget=0)["thinking_budget"] == 0

    def test_it_beats_the_deployment_setting(self):
        with patch.object(settings, "THINKING_BUDGET", 0):
            assert _built(thinking_budget=4096)["thinking_budget"] == 4096


class TestWhenNothingAsks:
    def test_the_deployment_setting_stands(self):
        with patch.object(settings, "THINKING_BUDGET", 1234):
            assert _built()["thinking_budget"] == 1234

    def test_a_negative_setting_still_hands_the_choice_to_the_model(self):
        with patch.object(settings, "THINKING_BUDGET", -1):
            assert "thinking_budget" not in _built()


class TestTheOtherArgumentsAreUntouched:
    @pytest.mark.parametrize("budget", [None, 0, 4096])
    def test_streaming_and_retries_survive_an_override(self, budget):
        built = _built(thinking_budget=budget)
        assert built["streaming"] is True
        assert built["max_retries"] == 2
