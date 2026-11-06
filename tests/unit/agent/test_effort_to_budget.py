"""What "answer carefully" costs the model, in tokens."""

from __future__ import annotations

import pytest

from agent.src.agent.reasoning_profiles import budget_for_effort


class TestTheThreeShippedEfforts:
    def test_low_turns_reasoning_off(self):
        assert budget_for_effort("low") == 0

    def test_medium_allows_some(self):
        assert budget_for_effort("medium") > 0

    def test_high_allows_more_than_medium(self):
        assert budget_for_effort("high") > budget_for_effort("medium")

    def test_each_is_a_ceiling_not_a_blank_cheque(self):
        for effort in ("low", "medium", "high"):
            assert budget_for_effort(effort) >= 0


class TestAnythingElse:
    def test_an_unknown_effort_leaves_the_setting_alone(self):
        assert budget_for_effort("enthusiastic") is None

    def test_an_empty_effort_leaves_it_alone(self):
        assert budget_for_effort("") is None

    @pytest.mark.parametrize("odd", [None, 7, [], {}])
    def test_a_shape_it_cannot_read_leaves_it_alone(self, odd):
        assert budget_for_effort(odd) is None

    def test_case_does_not_matter(self):
        assert budget_for_effort("HIGH") == budget_for_effort("high")


class TestTheyAreActuallyDifferent:
    def test_no_two_efforts_ask_for_the_same_thing(self):
        budgets = {budget_for_effort(one) for one in ("low", "medium", "high")}
        assert len(budgets) == 3
