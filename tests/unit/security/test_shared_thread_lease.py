"""Only one run at a time on a conversation, across every pod."""

from __future__ import annotations

import pytest

from agent.src.security.shared_thread_lease import SharedThreadLeases


class _Redis:
    """Enough of the client to show the lease uses it correctly."""

    def __init__(self):
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return None
        self.values[key] = value
        if ex:
            self.ttls[key] = ex
        return True

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        return 1 if self.values.pop(key, None) is not None else 0


def _leases(redis=None):
    return SharedThreadLeases(client=redis or _Redis())


class TestTakingIt:
    @pytest.mark.asyncio
    async def test_a_free_conversation_is_granted(self):
        found = await _leases().claim(thread="t1", subject="amar")
        assert found.granted is True

    @pytest.mark.asyncio
    async def test_the_holder_is_reported_back(self):
        found = await _leases().claim(thread="t1", subject="amar")
        assert found.held_by == "amar"

    @pytest.mark.asyncio
    async def test_the_same_person_may_claim_again(self):
        leases = _leases()
        await leases.claim(thread="t1", subject="amar")
        found = await leases.claim(thread="t1", subject="amar")
        assert found.granted is True


class TestSomebodyElseHoldingIt:
    @pytest.mark.asyncio
    async def test_the_second_person_is_refused(self):
        leases = _leases()
        await leases.claim(thread="t1", subject="amar")
        found = await leases.claim(thread="t1", subject="bea")
        assert found.granted is False

    @pytest.mark.asyncio
    async def test_and_told_who_has_it(self):
        leases = _leases()
        await leases.claim(thread="t1", subject="amar")
        found = await leases.claim(thread="t1", subject="bea")
        assert found.held_by == "amar"

    @pytest.mark.asyncio
    async def test_another_conversation_is_unaffected(self):
        leases = _leases()
        await leases.claim(thread="t1", subject="amar")
        found = await leases.claim(thread="t2", subject="bea")
        assert found.granted is True


class TestEveryPodSeesIt:
    @pytest.mark.asyncio
    async def test_a_lease_taken_on_one_pod_blocks_another(self):
        shared = _Redis()
        pod_one, pod_two = _leases(shared), _leases(shared)
        await pod_one.claim(thread="t1", subject="amar")
        found = await pod_two.claim(thread="t1", subject="bea")
        assert found.granted is False and found.held_by == "amar"

    @pytest.mark.asyncio
    async def test_releasing_on_one_frees_it_on_the_other(self):
        shared = _Redis()
        pod_one, pod_two = _leases(shared), _leases(shared)
        await pod_one.claim(thread="t1", subject="amar")
        await pod_one.release(thread="t1", subject="amar")
        assert (await pod_two.claim(thread="t1", subject="bea")).granted is True


class TestLettingGo:
    @pytest.mark.asyncio
    async def test_the_holder_may_release_it(self):
        leases = _leases()
        await leases.claim(thread="t1", subject="amar")
        await leases.release(thread="t1", subject="amar")
        assert (await leases.claim(thread="t1", subject="bea")).granted is True

    @pytest.mark.asyncio
    async def test_somebody_else_cannot_release_it(self):
        leases = _leases()
        await leases.claim(thread="t1", subject="amar")
        await leases.release(thread="t1", subject="bea")
        assert (await leases.claim(thread="t1", subject="bea")).granted is False

    @pytest.mark.asyncio
    async def test_releasing_one_nobody_holds_is_harmless(self):
        await _leases().release(thread="t1", subject="amar")


class TestItExpires:
    @pytest.mark.asyncio
    async def test_a_lease_is_given_a_lifetime(self):
        redis = _Redis()
        await _leases(redis).claim(thread="t1", subject="amar")
        assert any(ttl > 0 for ttl in redis.ttls.values())


class TestWhenTheStoreIsDown:
    @pytest.mark.asyncio
    async def test_the_run_is_allowed(self):
        class _Down:
            async def set(self, *a, **k):
                raise ConnectionError("redis down")

            async def get(self, key):
                raise ConnectionError("redis down")

            async def delete(self, key):
                raise ConnectionError("redis down")

        found = await _leases(_Down()).claim(thread="t1", subject="amar")
        assert found.granted is True

    @pytest.mark.asyncio
    async def test_releasing_does_not_raise_either(self):
        class _Down:
            async def delete(self, key):
                raise ConnectionError("redis down")

        await _leases(_Down()).release(thread="t1", subject="amar")


class TestTheDoorUsesIt:
    """A lease nothing takes refuses nobody."""

    @staticmethod
    def _app(holder=None):

        from fastapi import FastAPI
        from starlette.testclient import TestClient

        from agent.aegra.inbound_limit_middleware import InboundLimitMiddleware
        from agent.src.security.thread_lease import Claim

        app = FastAPI()

        @app.post("/threads/t1/runs/wait")
        async def start():
            return {"ok": True}

        @app.get("/threads/t1/state")
        async def read():
            return {"ok": True}

        async def _caller(_request):
            return "bea"

        async def _claim(thread, subject):
            if holder and holder != subject:
                return Claim(granted=False, held_by=holder)
            return Claim(granted=True, held_by=subject)

        async def _no_spend(_key):
            return __import__("decimal").Decimal("0")

        async def _no_teams(_request):
            return ()

        app.add_middleware(
            InboundLimitMiddleware,
            limits=lambda: None,
            caller_of=_caller,
            spent_by=_no_spend,
            allowance=lambda: __import__(
                "agent.src.limits.fair_share", fromlist=["Allowance"]
            ).Allowance(per_person=None, per_team=None),
            team_spend=_no_spend,
            teams_of=_no_teams,
            claim_thread=_claim,
        )
        return TestClient(app)

    def test_a_free_conversation_runs(self):
        assert self._app().post("/threads/t1/runs/wait").status_code == 200

    def test_a_second_run_is_refused(self):
        assert self._app(holder="amar").post("/threads/t1/runs/wait").status_code == 409

    def test_the_refusal_names_who_holds_it(self):
        found = self._app(holder="amar").post("/threads/t1/runs/wait")
        assert "amar" in found.json()["detail"]

    def test_it_is_machine_readable(self):
        found = self._app(holder="amar").post("/threads/t1/runs/wait")
        assert found.json()["error_type"] == "thread_busy"

    def test_reading_the_conversation_is_still_allowed(self):
        assert self._app(holder="amar").get("/threads/t1/state").status_code == 200


class TestTheLeaseIsGivenBack:
    """Held for the run, not for the lifetime of the lease."""

    @staticmethod
    def _app(fail=False):
        from decimal import Decimal

        from fastapi import FastAPI
        from starlette.testclient import TestClient

        from agent.aegra.inbound_limit_middleware import InboundLimitMiddleware
        from agent.src.limits.fair_share import Allowance
        from agent.src.security.thread_lease import Claim

        released: list[tuple[str, str]] = []
        app = FastAPI()

        @app.post("/threads/t1/runs/wait")
        async def start():
            if fail:
                raise RuntimeError("the run threw")
            return {"ok": True}

        async def _caller(_request):
            return "bea"

        async def _claim(thread, subject):
            return Claim(granted=True, held_by=subject)

        async def _release(thread, subject):
            released.append((thread, subject))

        async def _zero(_key):
            return Decimal("0")

        async def _no_teams(_request):
            return ()

        app.add_middleware(
            InboundLimitMiddleware,
            limits=lambda: None,
            caller_of=_caller,
            spent_by=_zero,
            allowance=lambda: Allowance(per_person=None, per_team=None),
            team_spend=_zero,
            teams_of=_no_teams,
            claim_thread=_claim,
            release_thread=_release,
        )
        return TestClient(app, raise_server_exceptions=False), released

    def test_a_finished_run_frees_the_conversation(self):
        client, released = self._app()
        client.post("/threads/t1/runs/wait")
        assert released == [("t1", "bea")]

    def test_a_run_that_threw_frees_it_too(self):
        client, released = self._app(fail=True)
        client.post("/threads/t1/runs/wait")
        assert released == [("t1", "bea")]
