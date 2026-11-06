"""Who pays for work nobody was sitting in front of."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from agent.src.infrastructure.backend import attribution_from_runtime


class _Runtime:
    def __init__(self, config):
        self.config = config


def _runtime(**bag):
    return _Runtime({"metadata": {"user_id": "alice", **bag}})


class TestReadingWhatTheRunSaysAboutItself:
    def test_an_ordinary_run_is_started_by_a_person(self):
        assert attribution_from_runtime(_runtime())["started_by"] == "person"

    def test_a_run_that_says_it_is_scheduled_is(self):
        found = attribution_from_runtime(_runtime(started_by="schedule"))
        assert found["started_by"] == "schedule"

    def test_a_project_is_read_when_one_is_named(self):
        assert attribution_from_runtime(_runtime(project="atlas"))["project"] == "atlas"

    def test_no_project_is_no_project(self):
        assert attribution_from_runtime(_runtime())["project"] == ""

    def test_something_that_is_not_a_known_starter_is_a_person(self):
        found = attribution_from_runtime(_runtime(started_by="pigeon"))
        assert found["started_by"] == "person"

    def test_the_configurable_bag_works_too(self):
        found = attribution_from_runtime(
            _Runtime({"configurable": {"started_by": "schedule"}})
        )
        assert found["started_by"] == "schedule"

    def test_a_runtime_with_no_config_is_a_person(self):
        assert attribution_from_runtime(_Runtime(None))["started_by"] == "person"

    def test_nothing_at_all_is_a_person(self):
        assert attribution_from_runtime(None)["started_by"] == "person"

    def test_a_config_of_the_wrong_shape_does_not_raise(self):
        assert attribution_from_runtime(_Runtime("not a mapping"))["project"] == ""


class TestWhoEndsUpPaying:
    @staticmethod
    async def _billed(**facts):
        from agent.src.infrastructure.middleware import _record_caller_spend

        seen = []

        async def _charge(run, **kwargs):
            seen.append(run)

        with (
            patch("agent.src.security.caller_spend.record", return_value=None),
            patch(
                "agent.src.infrastructure.middleware._teams_with_a_budget",
                return_value=facts.pop("teams", ()),
            ),
            patch(
                "agent.src.security.cost_attribution.charge_for",
                side_effect=_charge,
            ),
        ):
            await _record_caller_spend("alice", Decimal("0.40"), context=facts)

        from agent.src.security.cost_attribution import attribute

        return attribute(seen[0]).charged_to

    @pytest.mark.asyncio
    async def test_an_ordinary_run_is_billed_to_the_person(self):
        assert await self._billed() == "alice"

    @pytest.mark.asyncio
    async def test_a_scheduled_run_with_no_team_is_not(self):
        assert await self._billed(started_by="schedule") != "alice"

    @pytest.mark.asyncio
    async def test_a_scheduled_run_with_a_team_belongs_to_the_team(self):
        assert await self._billed(started_by="schedule", teams=("platform",)) == (
            "platform"
        )

    @pytest.mark.asyncio
    async def test_a_named_project_pays_before_a_team(self):
        found = await self._billed(project="atlas", teams=("research",))
        assert found == "atlas"

    @pytest.mark.asyncio
    async def test_who_ran_it_is_kept_either_way(self):
        from agent.src.infrastructure.middleware import _record_caller_spend

        seen = []

        async def _charge(run, **kwargs):
            seen.append(run)

        with (
            patch("agent.src.security.caller_spend.record", return_value=None),
            patch(
                "agent.src.infrastructure.middleware._teams_with_a_budget",
                return_value=(),
            ),
            patch(
                "agent.src.security.cost_attribution.charge_for",
                side_effect=_charge,
            ),
        ):
            await _record_caller_spend(
                "alice", Decimal("0.40"), context={"started_by": "schedule"}
            )

        assert seen[0].person == "alice"

    @pytest.mark.asyncio
    async def test_called_without_any_context_still_works(self):
        assert await self._billed() == "alice"


class TestTheCountersAreUnchanged:
    @pytest.mark.asyncio
    async def test_a_scheduled_run_still_counts_against_the_person(self):
        from agent.src.infrastructure.middleware import _record_caller_spend

        charged = []
        with (
            patch(
                "agent.src.security.caller_spend.record",
                side_effect=lambda who, amount: charged.append(who),
            ),
            patch(
                "agent.src.infrastructure.middleware._teams_with_a_budget",
                return_value=(),
            ),
            patch("agent.src.security.cost_attribution.charge_for", return_value=None),
        ):
            await _record_caller_spend(
                "alice", Decimal("0.40"), context={"started_by": "schedule"}
            )
        assert "alice" in charged


class TestTheRunActuallySaysSo:
    """The facts have to arrive from the run, not be invented."""

    @staticmethod
    async def _reported(config):
        from agent.src.security.spend_middleware import SpendLimitMiddleware

        seen = []

        async def _spent(caller, amount, *, context=None):
            seen.append((caller, context))

        middleware = SpendLimitMiddleware(on_spent=_spent)
        middleware.spent = Decimal("0.40")
        await middleware.aafter_agent({}, _Runtime(config))
        return seen

    @pytest.mark.asyncio
    async def test_an_ordinary_run_reports_a_person(self):
        found = await self._reported({"metadata": {"user_id": "alice"}})
        assert found[0][1]["started_by"] == "person"

    @pytest.mark.asyncio
    async def test_a_scheduled_run_says_so(self):
        found = await self._reported(
            {"metadata": {"user_id": "alice", "started_by": "schedule"}}
        )
        assert found[0][1]["started_by"] == "schedule"

    @pytest.mark.asyncio
    async def test_a_project_travels_with_it(self):
        found = await self._reported(
            {"metadata": {"user_id": "alice", "project": "atlas"}}
        )
        assert found[0][1]["project"] == "atlas"

    @pytest.mark.asyncio
    async def test_the_caller_is_still_reported(self):
        found = await self._reported({"metadata": {"user_id": "alice"}})
        assert found[0][0] == "alice"

    @pytest.mark.asyncio
    async def test_a_run_that_cost_nothing_reports_nothing(self):
        from agent.src.security.spend_middleware import SpendLimitMiddleware

        seen = []

        async def _spent(caller, amount, *, context=None):
            seen.append(caller)

        middleware = SpendLimitMiddleware(on_spent=_spent)
        await middleware.aafter_agent({}, _Runtime({"metadata": {"user_id": "alice"}}))
        assert seen == []
