"""Holding an inbound caller to its own limits at the door."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from agent.aegra.inbound_limit_middleware import InboundLimitMiddleware
from agent.src.security.inbound_limits import Limits

TIGHT = Limits(per_second=100, burst=100, daily_spend=Decimal("5.00"))


def _app(limits, spent=Decimal("0"), caller="svc-a"):
    app = FastAPI()

    @app.post("/threads/t1/runs/wait")
    async def start():
        return {"ok": True}

    @app.post("/runs")
    async def start_plain():
        return {"ok": True}

    @app.get("/threads/t1/state")
    async def read():
        return {"ok": True}

    async def _caller(_request):
        return caller

    async def _spent(_caller):
        return spent

    app.add_middleware(
        InboundLimitMiddleware,
        limits=lambda: limits,
        caller_of=_caller,
        spent_by=_spent,
    )
    return TestClient(app)


class TestWhenLimitsAreOff:
    def test_a_run_starts(self):
        assert _app(None).post("/threads/t1/runs/wait").status_code == 200

    def test_even_for_a_caller_that_has_spent_everything(self):
        found = _app(None, spent=Decimal("900")).post("/threads/t1/runs/wait")
        assert found.status_code == 200

    def test_nothing_is_looked_up(self):
        called = []

        async def _spent(_caller):
            called.append(_caller)
            return Decimal("0")

        async def _caller(_request):
            return "svc-a"

        app = FastAPI()

        @app.post("/runs")
        async def start():
            return {"ok": True}

        app.add_middleware(
            InboundLimitMiddleware,
            limits=lambda: None,
            caller_of=_caller,
            spent_by=_spent,
        )
        TestClient(app).post("/runs")
        assert called == []


class TestWhatIsGated:
    def test_a_run_start_is(self):
        found = _app(TIGHT, spent=Decimal("9")).post("/threads/t1/runs/wait")
        assert found.status_code == 429

    def test_a_plain_run_start_is(self):
        assert _app(TIGHT, spent=Decimal("9")).post("/runs").status_code == 429

    def test_reading_a_run_already_in_flight_is_not(self):
        found = _app(TIGHT, spent=Decimal("9")).get("/threads/t1/state")
        assert found.status_code == 200


class TestTheRefusal:
    def test_it_is_a_429_not_a_500(self):
        found = _app(TIGHT, spent=Decimal("9")).post("/runs")
        assert found.status_code == 429

    def test_it_says_which_limit(self):
        found = _app(TIGHT, spent=Decimal("9")).post("/runs")
        assert "spend" in found.json()["detail"].lower()

    def test_it_carries_retry_after(self):
        found = _app(TIGHT, spent=Decimal("9")).post("/runs")
        assert int(found.headers["Retry-After"]) > 0

    def test_it_is_machine_readable(self):
        found = _app(TIGHT, spent=Decimal("9")).post("/runs")
        assert found.json()["error_type"] == "caller_limit"


class TestACallerItCannotIdentify:
    def test_it_is_refused_while_limits_are_on(self):
        found = _app(TIGHT, caller="").post("/runs")
        assert found.status_code == 429

    def test_it_is_admitted_while_they_are_off(self):
        assert _app(None, caller="").post("/runs").status_code == 200


class TestWhenTheCounterCannotBeRead:
    def test_the_run_still_starts(self):
        async def _broken(_caller):
            raise ConnectionError("no redis")

        async def _caller(_request):
            return "svc-a"

        app = FastAPI()

        @app.post("/runs")
        async def start():
            return {"ok": True}

        app.add_middleware(
            InboundLimitMiddleware,
            limits=lambda: TIGHT,
            caller_of=_caller,
            spent_by=_broken,
        )
        assert TestClient(app).post("/runs").status_code == 200


class TestTheIdentityItUses:
    @pytest.mark.asyncio
    async def test_it_is_the_verified_one(self):
        from agent.aegra.inbound_limit_middleware import caller_of

        with patch(
            "agent.aegra.auth_helpers.memory_user_id",
            return_value="svc-a",
        ) as verified:
            assert await caller_of(object()) == "svc-a"
        assert verified.called

    @pytest.mark.asyncio
    async def test_a_caller_it_cannot_verify_has_no_identity(self):
        from agent.aegra.inbound_limit_middleware import caller_of

        with patch(
            "agent.aegra.auth_helpers.memory_user_id",
            side_effect=ValueError("bad token"),
        ):
            assert await caller_of(object()) == ""

    @pytest.mark.asyncio
    async def test_an_anonymous_caller_has_no_identity(self):
        from agent.aegra.inbound_limit_middleware import caller_of

        with patch(
            "agent.aegra.auth_helpers.memory_user_id",
            return_value="anonymous",
        ):
            assert await caller_of(object()) == ""


class TestWhatVerifiedMeansHere:
    """The budget key is checked, not merely claimed."""

    @pytest.mark.asyncio
    async def test_a_header_that_contradicts_the_token_is_refused(self):
        from agent.aegra.auth_helpers import memory_user_id

        class _Request:
            headers = {
                "x-user-id": "somebody-else",
                "authorization": "Bearer token",
            }

        with (
            patch("agent.aegra.auth.ENABLE_AUTH", True),
            patch(
                "agent.aegra.auth._decode_token",
                return_value={"preferred_username": "johnwick"},
            ),
            pytest.raises(Exception) as refused,
        ):
            await memory_user_id(_Request())

        assert "403" in str(refused.value) or "match" in str(refused.value)

    @pytest.mark.asyncio
    async def test_the_door_uses_the_token_not_the_header(self):
        from agent.aegra.inbound_limit_middleware import caller_of

        class _Request:
            headers = {"authorization": "Bearer token"}

        with (
            patch("agent.aegra.auth.ENABLE_AUTH", True),
            patch(
                "agent.aegra.auth._decode_token",
                return_value={"preferred_username": "johnwick"},
            ),
        ):
            assert await caller_of(_Request()) == "johnwick"
