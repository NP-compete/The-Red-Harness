"""A ceiling the orchestrator respects and subagents ignore is not a ceiling."""

from __future__ import annotations

from unittest.mock import patch

from agent.src.infrastructure.subagents import _subagent_middleware
from agent.src.security.spend_middleware import SpendLimitMiddleware


def _built(warn_at: str = "", refuse_at: str = "") -> list:
    from agent.src.agent.config.middleware import SpendLimitConfig

    resolved = type(
        "R",
        (),
        {
            "tool_call_limit": type("T", (), {"per_tool": {}})(),
            "spend_limit": SpendLimitConfig(warn_at=warn_at, refuse_at=refuse_at),
        },
    )()
    with patch(
        "agent.src.infrastructure.subagents.agent_config.resolve_agent_middleware",
        return_value=resolved,
    ):
        return _subagent_middleware("curator", [], []) or []


def _caps(built: list) -> list:
    return [m for m in built if isinstance(m, SpendLimitMiddleware)]


def test_a_subagent_is_capped_when_the_deployment_sets_one():
    assert _caps(_built(refuse_at="1.00"))


def test_the_subagent_cap_carries_the_configured_ceiling():
    from decimal import Decimal

    cap = _caps(_built(refuse_at="1.00"))[0]
    assert cap._cap.refuse_at == Decimal("1.00")


def test_the_subagent_cap_carries_the_warning_too():
    from decimal import Decimal

    cap = _caps(_built(warn_at="0.50", refuse_at="1.00"))[0]
    assert cap._cap.warn_at == Decimal("0.50")


def test_a_deployment_with_no_ceiling_adds_nothing():
    assert _caps(_built()) == []


def test_each_subagent_gets_its_own_tally():
    """Sharing one accumulator across concurrent runs would leak"""
    first = _caps(_built(refuse_at="1.00"))[0]
    second = _caps(_built(refuse_at="1.00"))[0]
    assert first is not second


def test_a_ceiling_that_cannot_be_read_does_not_take_the_subagent_with_it():
    """A broken ceiling is reported and skipped, not raised through the"""
    from unittest.mock import MagicMock

    from agent.src.infrastructure.subagents import _build_subagent_spend_limit

    assert _build_subagent_spend_limit(MagicMock()) is None


def test_a_config_without_the_section_adds_nothing():
    from agent.src.infrastructure.subagents import _build_subagent_spend_limit

    assert _build_subagent_spend_limit(object()) is None
