"""Asking what you have left."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from agent.src.limits.fair_share import Allowance

CAPPED = Allowance(per_person=Decimal("5.00"), per_team=Decimal("20.00"))
UNCAPPED = Allowance(per_person=None, per_team=None)


@pytest.fixture
def client() -> TestClient:
    from agent.aegra.http_app import app

    return TestClient(app)


def _asked(
    client,
    *,
    allowance=CAPPED,
    person=Decimal("1.25"),
    team=Decimal("8.00"),
    teams=("platform",),
):
    async def _spent(key):
        return team if key.startswith("team:") else person

    with (
        patch(
            "agent.src.agent.config.loader.AgentConfig.get_limits_config",
            return_value=allowance,
        ),
        patch("agent.aegra.limits_routes._who", return_value="alice"),
        patch("agent.aegra.limits_routes._teams_of", return_value=teams),
        patch("agent.aegra.limits_routes._spent_today", side_effect=_spent),
    ):
        return client.get("/limits/mine")


class TestWhatComesBack:
    def test_it_answers(self, client):
        assert _asked(client).status_code == 200

    def test_it_says_what_they_have_spent(self, client):
        assert _asked(client).json()["person"]["spent"] == "1.25"

    def test_it_says_what_is_left(self, client):
        assert _asked(client).json()["person"]["remaining"] == "3.75"

    def test_it_says_the_same_for_the_team(self, client):
        assert _asked(client).json()["team"]["remaining"] == "12.00"

    def test_somebody_in_no_team_has_no_team_side(self, client):
        assert _asked(client, teams=()).json()["team"] is None


class TestWhenNothingIsCapped:
    def test_it_still_answers(self, client):
        assert _asked(client, allowance=UNCAPPED).status_code == 200

    def test_it_reports_no_limit_rather_than_zero(self, client):
        found = _asked(client, allowance=UNCAPPED).json()
        assert found["person"]["limit"] is None

    def test_and_still_reports_the_spending(self, client):
        found = _asked(client, allowance=UNCAPPED).json()
        assert found["person"]["spent"] == "1.25"


class TestWhenTheCounterCannotBeRead:
    def test_it_does_not_fail_the_request(self, client):
        async def _broken(key):
            raise ConnectionError("counter unavailable")

        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_limits_config",
                return_value=CAPPED,
            ),
            patch("agent.aegra.limits_routes._who", return_value="alice"),
            patch("agent.aegra.limits_routes._teams_of", return_value=()),
            patch("agent.aegra.limits_routes._spent_today", side_effect=_broken),
        ):
            found = client.get("/limits/mine")
        assert found.status_code == 200

    def test_and_says_it_could_not_tell(self, client):
        async def _broken(key):
            raise ConnectionError("counter unavailable")

        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_limits_config",
                return_value=CAPPED,
            ),
            patch("agent.aegra.limits_routes._who", return_value="alice"),
            patch("agent.aegra.limits_routes._teams_of", return_value=()),
            patch("agent.aegra.limits_routes._spent_today", side_effect=_broken),
        ):
            found = client.get("/limits/mine").json()
        assert found["unreadable"] is True


MONTHLY = Allowance(
    per_person=Decimal("5.00"),
    per_team=Decimal("20.00"),
    per_person_month=Decimal("100.00"),
    per_team_month=Decimal("900.00"),
    teams=("platform",),
)


def _asked_monthly(client, *, month=Decimal("60.00"), team_month=Decimal("90.00")):
    async def _spent(key):
        return Decimal("8.00") if key.startswith("team:") else Decimal("1.25")

    async def _month(key):
        return team_month if key.startswith("team:") else month

    with (
        patch(
            "agent.src.agent.config.loader.AgentConfig.get_limits_config",
            return_value=MONTHLY,
        ),
        patch("agent.aegra.limits_routes._who", return_value="alice"),
        patch("agent.aegra.limits_routes._teams_of", return_value=("platform",)),
        patch("agent.aegra.limits_routes._spent_today", side_effect=_spent),
        patch("agent.aegra.limits_routes._spent_this_month", side_effect=_month),
    ):
        return client.get("/limits/mine")


class TestTheMonthComesBackToo:
    """Being stopped by a monthly budget on the 22nd is not a"""

    def test_the_forecast_is_there(self, client):
        assert _asked_monthly(client).json()["forecast"]["person"] is not None

    def test_it_reports_the_month_so_far(self, client):
        assert _asked_monthly(client).json()["forecast"]["person"]["spent"] == "60.00"

    def test_it_says_where_the_month_is_heading(self, client):
        found = _asked_monthly(client).json()["forecast"]["person"]
        assert found["verdict"] in {"on-track", "will-overrun", "exhausted"}

    def test_the_team_month_is_there(self, client):
        assert _asked_monthly(client).json()["forecast"]["team"] is not None

    def test_the_daily_numbers_are_still_there(self, client):
        assert _asked_monthly(client).json()["person"]["remaining"] == "3.75"

    def test_no_monthly_cap_means_no_forecast(self, client):
        assert _asked(client).json()["forecast"]["person"] is None

    def test_a_counter_that_is_down_does_not_lose_the_page(self, client):
        async def _broken(key):
            raise RuntimeError("redis is down")

        async def _spent(key):
            return Decimal("1.25")

        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_limits_config",
                return_value=MONTHLY,
            ),
            patch("agent.aegra.limits_routes._who", return_value="alice"),
            patch("agent.aegra.limits_routes._teams_of", return_value=("platform",)),
            patch("agent.aegra.limits_routes._spent_today", side_effect=_spent),
            patch("agent.aegra.limits_routes._spent_this_month", side_effect=_broken),
        ):
            found = client.get("/limits/mine")

        assert found.status_code == 200
        assert found.json()["unreadable"] is True
