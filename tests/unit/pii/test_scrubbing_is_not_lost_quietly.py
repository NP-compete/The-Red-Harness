"""Losing PII scrubbing should be loud."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.src.pii.config import PIIConfig, PIIRule


def _rule():
    return PIIRule(name="email", pattern=r"[^@\s]+@[^@\s]+")


def _warned(config):
    from agent.src.infrastructure import middleware

    said = []
    with patch.object(middleware, "logger") as log:
        middleware.warn_if_unscrubbed(config)
        said.extend(str(call) for call in log.warning.call_args_list)
    return said


class TestWhenScrubbingIsOff:
    def test_it_says_something(self):
        assert _warned(PIIConfig(enabled=False))

    def test_it_says_what_is_not_happening(self):
        said = str(_warned(PIIConfig(enabled=False)))
        assert "scrub" in said.lower() or "redact" in said.lower()

    def test_it_says_where_that_text_goes(self):
        said = str(_warned(PIIConfig(enabled=False))).lower()
        assert "model" in said or "trace" in said


class TestWhenItIsOnButDoesNothing:
    def test_rules_that_are_empty_are_the_same_as_off(self):
        assert _warned(PIIConfig(enabled=True, rules=[]))

    def test_the_warning_distinguishes_the_two(self):
        off = str(_warned(PIIConfig(enabled=False)))
        empty = str(_warned(PIIConfig(enabled=True, rules=[])))
        assert off != empty


class TestWhenItIsWorking:
    def test_nothing_is_said(self):
        assert _warned(PIIConfig(enabled=True, rules=[_rule()])) == []


class TestItIsCalledWhereTheMiddlewareIsBuilt:
    def test_the_builder_checks(self):
        import inspect

        from agent.src.infrastructure import middleware

        assert "warn_if_unscrubbed" in inspect.getsource(middleware._append_guardrails)

    @pytest.mark.parametrize("enabled", [True, False])
    def test_a_check_that_fails_does_not_stop_the_agent(self, enabled):
        from agent.src.infrastructure.middleware import warn_if_unscrubbed

        class _Odd:
            @property
            def enabled(self):
                raise RuntimeError("unreadable")

        warn_if_unscrubbed(_Odd())
