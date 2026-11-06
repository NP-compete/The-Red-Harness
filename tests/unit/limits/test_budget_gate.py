"""Refusing a run that would go over somebody's allowance."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from agent.src.limits.fair_share import Allowance

CAPPED = Allowance(per_person=Decimal("5.00"), per_team=None)


async def _no_teams(_request):
    return ()


async def _the_platform_team(_request):
    return ("platform",)


UNCAPPED = Allowance(per_person=None, per_team=None)


def _app(allowance, *, spent=Decimal("0"), caller="alice"):
    from agent.aegra.inbound_limit_middleware import InboundLimitMiddleware

    app = FastAPI()

    @app.post("/threads/t1/runs/wait")
    async def start():
        return {"ok": True}

    @app.get("/threads/t1/state")
    async def read():
        return {"ok": True}

    async def _caller(_request):
        return caller

    async def _spent(_key):
        return spent

    app.add_middleware(
        InboundLimitMiddleware,
        limits=lambda: None,
        caller_of=_caller,
        spent_by=_spent,
        allowance=lambda: allowance,
        team_spend=_spent,
        teams_of=_no_teams,
    )
    return TestClient(app)


class TestWhenThereIsRoom:
    def test_a_run_starts(self):
        found = _app(CAPPED, spent=Decimal("1.00")).post("/threads/t1/runs/wait")
        assert found.status_code == 200

    def test_with_no_cap_at_all(self):
        found = _app(UNCAPPED, spent=Decimal("900")).post("/threads/t1/runs/wait")
        assert found.status_code == 200


class TestWhenTheAllowanceIsSpent:
    def test_the_run_is_refused(self):
        found = _app(CAPPED, spent=Decimal("5.00")).post("/threads/t1/runs/wait")
        assert found.status_code == 429

    def test_the_refusal_says_it_was_their_own_allowance(self):
        found = _app(CAPPED, spent=Decimal("5.00")).post("/threads/t1/runs/wait")
        assert "your own" in found.json()["detail"]

    def test_it_is_machine_readable(self):
        found = _app(CAPPED, spent=Decimal("5.00")).post("/threads/t1/runs/wait")
        assert found.json()["error_type"] == "over_budget"

    def test_it_says_when_to_come_back(self):
        found = _app(CAPPED, spent=Decimal("5.00")).post("/threads/t1/runs/wait")
        assert int(found.headers["Retry-After"]) >= 60

    def test_reading_is_still_allowed(self):
        found = _app(CAPPED, spent=Decimal("5.00")).get("/threads/t1/state")
        assert found.status_code == 200


class TestWhenTheCounterIsDown:
    def test_the_run_is_allowed(self):
        from agent.aegra.inbound_limit_middleware import InboundLimitMiddleware

        app = FastAPI()

        @app.post("/threads/t1/runs/wait")
        async def start():
            return {"ok": True}

        async def _broken(_key):
            raise ConnectionError("counter unavailable")

        async def _caller(_request):
            return "alice"

        app.add_middleware(
            InboundLimitMiddleware,
            limits=lambda: None,
            caller_of=_caller,
            spent_by=_broken,
            allowance=lambda: CAPPED,
            team_spend=_broken,
            teams_of=_no_teams,
        )
        assert TestClient(app).post("/threads/t1/runs/wait").status_code == 200


class TestTheTeamSide:
    @staticmethod
    def _with_team(person, team):
        from agent.aegra.inbound_limit_middleware import InboundLimitMiddleware

        app = FastAPI()

        @app.post("/threads/t1/runs/wait")
        async def start():
            return {"ok": True}

        async def _caller(_request):
            return "alice"

        async def _person(_key):
            return person

        async def _team(_name):
            return team

        app.add_middleware(
            InboundLimitMiddleware,
            limits=lambda: None,
            caller_of=_caller,
            spent_by=_person,
            allowance=lambda: Allowance(
                per_person=Decimal("5.00"),
                per_team=Decimal("20.00"),
                teams=("platform",),
            ),
            team_spend=_team,
            teams_of=_the_platform_team,
        )
        return TestClient(app).post("/threads/t1/runs/wait")

    def test_a_full_team_refuses_a_person_with_room(self):
        assert self._with_team(Decimal("1.00"), Decimal("20.00")).status_code == 429

    def test_and_says_it_was_the_team(self):
        found = self._with_team(Decimal("1.00"), Decimal("20.00"))
        assert "team" in found.json()["detail"]

    def test_a_person_over_their_own_is_told_that_instead(self):
        found = self._with_team(Decimal("5.00"), Decimal("20.00"))
        assert "your own" in found.json()["detail"]

    @pytest.mark.parametrize("team_spent", ["0", "19.99"])
    def test_room_on_both_sides_runs(self, team_spent):
        found = self._with_team(Decimal("1.00"), Decimal(team_spent))
        assert found.status_code == 200


class TestRecordingWhatARunCost:
    """A team counter nothing increments reads as a team that"""

    @pytest.mark.asyncio
    async def test_the_person_is_charged(self):

        from agent.src.infrastructure.middleware import _record_caller_spend

        charged = []
        with (
            patch(
                "agent.src.security.caller_spend.record",
                side_effect=lambda who, amount: charged.append((who, amount)),
            ),
            patch(
                "agent.src.infrastructure.middleware._teams_with_a_budget",
                return_value=(),
            ),
        ):
            await _record_caller_spend("alice", Decimal("0.40"))
        assert ("alice", Decimal("0.40")) in charged

    @pytest.mark.asyncio
    async def test_their_team_is_charged_too(self):

        from agent.src.infrastructure.middleware import _record_caller_spend

        charged = []
        with (
            patch(
                "agent.src.security.caller_spend.record",
                side_effect=lambda who, amount: charged.append((who, amount)),
            ),
            patch(
                "agent.src.infrastructure.middleware._teams_with_a_budget",
                return_value=("platform",),
            ),
        ):
            await _record_caller_spend("alice", Decimal("0.40"))
        assert ("team:platform", Decimal("0.40")) in charged

    @pytest.mark.asyncio
    async def test_a_team_lookup_that_fails_still_charges_the_person(self):

        from agent.src.infrastructure.middleware import _record_caller_spend

        charged = []
        with (
            patch(
                "agent.src.security.caller_spend.record",
                side_effect=lambda who, amount: charged.append((who, amount)),
            ),
            patch(
                "agent.src.infrastructure.middleware._teams_with_a_budget",
                side_effect=ConnectionError("directory down"),
            ),
        ):
            await _record_caller_spend("alice", Decimal("0.40"))
        assert ("alice", Decimal("0.40")) in charged


class TestAMonthlyCapIsAlsoCounting:
    """A counter nothing increments reads as nobody spending."""

    @staticmethod
    def _counting(allowance):
        from unittest.mock import patch

        from agent.src.infrastructure.middleware import _per_caller_cap_is_set

        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_limits_config",
                return_value=allowance,
            ),
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
                side_effect=RuntimeError("no inbound door here"),
            ),
        ):
            return _per_caller_cap_is_set()

    def test_a_monthly_personal_cap_counts(self):
        assert self._counting(
            Allowance(
                per_person=None, per_team=None, per_person_month=Decimal("100.00")
            )
        )

    def test_a_monthly_team_cap_counts(self):
        assert self._counting(
            Allowance(
                per_person=None,
                per_team=None,
                per_team_month=Decimal("900.00"),
                teams=("platform",),
            )
        )

    def test_a_daily_cap_still_counts(self):
        assert self._counting(Allowance(per_person=Decimal("5.00"), per_team=None))

    def test_no_cap_at_all_counts_nothing(self):
        assert not self._counting(Allowance(per_person=None, per_team=None))


class TestTheBillAsWellAsTheCap:
    """The counters refuse; the ledger bills."""

    @staticmethod
    async def _recorded(teams):
        from agent.src.infrastructure.middleware import _record_caller_spend

        billed = []

        async def _charge(run, **kwargs):
            billed.append(run)

        with (
            patch("agent.src.security.caller_spend.record", return_value=None),
            patch(
                "agent.src.infrastructure.middleware._teams_with_a_budget",
                return_value=teams,
            ),
            patch(
                "agent.src.security.cost_attribution.charge_for",
                side_effect=_charge,
            ),
        ):
            await _record_caller_spend("alice", Decimal("0.40"))
        return billed

    @pytest.mark.asyncio
    async def test_the_run_reaches_the_ledger(self):
        assert await self._recorded(())

    @pytest.mark.asyncio
    async def test_it_carries_who_ran_it(self):
        assert (await self._recorded(()))[0].person == "alice"

    @pytest.mark.asyncio
    async def test_it_carries_the_team_that_pays(self):
        assert (await self._recorded(("platform",)))[0].team == "platform"

    @pytest.mark.asyncio
    async def test_it_carries_what_the_run_cost(self):
        assert (await self._recorded(()))[0].amount == Decimal("0.40")

    @pytest.mark.asyncio
    async def test_a_ledger_that_fails_still_charges_the_counters(self):
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
            patch(
                "agent.src.security.cost_attribution.charge_for",
                side_effect=RuntimeError("ledger down"),
            ),
        ):
            await _record_caller_spend("alice", Decimal("0.40"))
        assert "alice" in charged


class TestTheDoorCountsTheSamePersonAsTheRun:
    """One name for a counter, or the cap protects nobody."""

    @pytest.mark.asyncio
    async def test_the_door_names_the_person_the_run_names(self):
        from unittest.mock import patch

        from agent.aegra.inbound_limit_middleware import caller_of
        from agent.src.infrastructure.backend import _get_user_id_from_runtime

        class _Request:
            headers = {"x-user-id": "johnwick"}

        class _Runtime:
            config = {"configurable": {"user_id": "johnwick"}}

        with patch("agent.aegra.auth.ENABLE_AUTH", False):
            at_the_door = await caller_of(_Request())

        assert at_the_door == _get_user_id_from_runtime(_Runtime())

    @pytest.mark.asyncio
    async def test_an_unnamed_caller_is_still_nobody(self):
        from unittest.mock import patch

        from agent.aegra.inbound_limit_middleware import caller_of

        class _Request:
            headers = {}

        with patch(
            "agent.aegra.auth_helpers.memory_user_id",
            side_effect=RuntimeError("no credentials"),
        ):
            assert await caller_of(_Request()) == ""
