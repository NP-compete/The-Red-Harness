"""A loop inside a subagent is still a loop."""

from __future__ import annotations

from unittest.mock import patch

from agent.src.agent.config.middleware import ToolCallLimitConfig
from agent.src.infrastructure.block_budget import BlockBudgetMiddleware
from agent.src.infrastructure.subagents import _subagent_middleware


def _built(**limits) -> list:
    resolved = type(
        "R",
        (),
        {
            "tool_call_limit": ToolCallLimitConfig(**limits),
            "spend_limit": None,
        },
    )()
    with patch(
        "agent.src.infrastructure.subagents.agent_config.resolve_agent_middleware",
        return_value=resolved,
    ):
        return _subagent_middleware("curator", [], []) or []


def _budgets(built: list) -> list:
    return [m for m in built if isinstance(m, BlockBudgetMiddleware)]


def test_a_block_ceiling_reaches_the_subagent():
    assert _budgets(_built(per_block=3))


def test_a_conversation_ceiling_reaches_the_subagent():
    assert _budgets(_built(per_thread=50))


def test_the_configured_ceiling_travels_with_it():
    budget = _budgets(_built(per_block=3))[0]
    assert budget._config.per_block == 3


def test_a_deployment_with_no_ceiling_adds_nothing():
    assert _budgets(_built()) == []


def test_a_config_without_the_section_adds_nothing():
    from agent.src.infrastructure.subagents import _build_subagent_budget

    assert _build_subagent_budget(object()) is None


def test_an_unreadable_ceiling_does_not_take_the_subagent_with_it():
    """One broken ceiling must not cost every subagent its build."""
    from unittest.mock import MagicMock

    from agent.src.infrastructure.subagents import _build_subagent_budget

    assert _build_subagent_budget(MagicMock()) is None
