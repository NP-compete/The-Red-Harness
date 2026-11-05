"""Holding one tool to a rate and a number in flight."""

from __future__ import annotations

import pytest

from agent.src.security.tool_pace import ToolPace


class TestNothingConfigured:
    def test_every_call_passes(self):
        pace = ToolPace.from_config({})
        for _ in range(100):
            assert pace.may_call("search", run="r1").permitted is True

    def test_and_nothing_is_tracked(self):
        pace = ToolPace.from_config({})
        pace.may_call("search", run="r1")
        assert pace.in_flight("search") == 0


class TestHowManyAtOnce:
    @staticmethod
    def _pace(limit=2):
        return ToolPace.from_config({"concurrency": {"default": limit}})

    def test_calls_up_to_the_limit_are_allowed(self):
        pace = self._pace()
        assert pace.may_call("search", run="r1").permitted is True
        assert pace.may_call("search", run="r2").permitted is True

    def test_one_more_is_refused(self):
        pace = self._pace()
        pace.may_call("search", run="r1")
        pace.may_call("search", run="r2")
        assert pace.may_call("search", run="r3").permitted is False

    def test_the_refusal_is_worth_retrying(self):
        pace = self._pace()
        pace.may_call("search", run="r1")
        pace.may_call("search", run="r2")
        assert pace.may_call("search", run="r3").retryable is True

    def test_finishing_one_frees_a_place(self):
        pace = self._pace()
        pace.may_call("search", run="r1")
        pace.may_call("search", run="r2")
        pace.done("search", run="r1")
        assert pace.may_call("search", run="r3").permitted is True

    def test_another_tool_is_unaffected(self):
        pace = self._pace()
        pace.may_call("search", run="r1")
        pace.may_call("search", run="r2")
        assert pace.may_call("write", run="r3").permitted is True

    def test_one_tool_may_be_given_its_own_number(self):
        pace = ToolPace.from_config(
            {"concurrency": {"default": 1, "per_tool": {"search": 3}}}
        )
        for run in ("r1", "r2", "r3"):
            assert pace.may_call("search", run=run).permitted is True


class TestHowOften:
    @staticmethod
    def _pace(per_second=2, burst=2):
        return ToolPace.from_config(
            {"rate": {"per_second": per_second, "burst": burst}}
        )

    def test_a_burst_is_allowed(self):
        pace = self._pace()
        assert pace.may_call("search", run="r1").permitted is True
        assert pace.may_call("search", run="r2").permitted is True

    def test_past_the_burst_is_refused(self):
        pace = self._pace()
        for run in ("r1", "r2", "r3"):
            found = pace.may_call("search", run=run)
        assert found.permitted is False

    def test_that_refusal_is_worth_retrying_too(self):
        pace = self._pace()
        for run in ("r1", "r2", "r3"):
            found = pace.may_call("search", run=run)
        assert found.retryable is True

    def test_each_tool_has_its_own_pace(self):
        pace = self._pace()
        for run in ("r1", "r2", "r3"):
            pace.may_call("search", run=run)
        assert pace.may_call("write", run="r4").permitted is True


class TestWhatTheModelIsTold:
    def test_the_refusal_names_the_tool(self):
        pace = ToolPace.from_config({"concurrency": {"default": 1}})
        pace.may_call("search", run="r1")
        assert "search" in pace.may_call("search", run="r2").reason

    def test_it_says_waiting_is_the_fix(self):
        pace = ToolPace.from_config({"concurrency": {"default": 1}})
        pace.may_call("search", run="r1")
        found = pace.may_call("search", run="r2")
        assert "already running" in found.reason or "too often" in found.reason


class TestSettingsThatWouldNotWork:
    def test_a_concurrency_of_nothing_is_refused(self):
        with pytest.raises(ValueError):
            ToolPace.from_config({"concurrency": {"default": 0}})

    def test_a_rate_of_nothing_is_refused(self):
        with pytest.raises(ValueError):
            ToolPace.from_config({"rate": {"per_second": 0, "burst": 1}})


class TestItRunsOnRealCalls:
    @staticmethod
    def _proxy(inner, pace):
        from unittest.mock import patch

        from agent.src.capability.manifest import CapabilityManifest
        from agent.src.capability.tool_proxy import CapabilityToolProxy

        proxy = CapabilityToolProxy(
            inner_tool=inner,
            manifest=CapabilityManifest(
                agent_name="test",
                allowed_tool_names=frozenset({inner.name}),
                source="EXPLICIT",
            ),
        )
        return proxy, patch(
            "agent.src.security.tool_preflight.configured_pace",
            return_value=pace,
        )

    class _Inner:
        name = "search"
        description = "search"
        args_schema = None

        def __init__(self):
            self.calls = 0

        async def ainvoke(self, value, config=None, **kwargs):
            self.calls += 1
            return "ran"

    @pytest.mark.asyncio
    async def test_a_call_within_the_limit_runs(self):
        pace = ToolPace.from_config({"concurrency": {"default": 2}})
        inner = self._Inner()
        proxy, patched = self._proxy(inner, pace)
        with patched:
            await proxy.ainvoke({})
        assert inner.calls == 1

    @pytest.mark.asyncio
    async def test_the_slot_is_given_back_afterwards(self):
        pace = ToolPace.from_config({"concurrency": {"default": 1}})
        inner = self._Inner()
        proxy, patched = self._proxy(inner, pace)
        with patched:
            await proxy.ainvoke({})
            await proxy.ainvoke({})
        assert inner.calls == 2

    @pytest.mark.asyncio
    async def test_it_is_given_back_when_the_tool_throws(self):
        class _Angry(self._Inner):
            async def ainvoke(self, value, config=None, **kwargs):
                self.calls += 1
                raise RuntimeError("the tool threw")

        pace = ToolPace.from_config({"concurrency": {"default": 1}})
        inner = _Angry()
        proxy, patched = self._proxy(inner, pace)
        with patched:
            for _ in range(2):
                try:
                    await proxy.ainvoke({})
                except RuntimeError:
                    pass
        assert inner.calls == 2
