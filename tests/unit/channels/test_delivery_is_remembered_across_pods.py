"""At-most-once survives a second replica (SCALE-1)."""

from __future__ import annotations

import pytest

from agent.src.channels import dispatch


class Channel:
    type = "webhook"


def _message():
    class Message:
        conversation = "C1"
        reply_to = "https://example.test/callback"
        metadata: dict = {}

    return Message()


@pytest.fixture(autouse=True)
def forget():
    dispatch._DELIVERED.clear()
    yield
    dispatch._DELIVERED.clear()


@pytest.fixture
def shared_redis(monkeypatch):
    """One Redis standing in for the whole deployment."""
    claimed: set[str] = set()

    async def run_redis(fn, /, *args, **kwargs):
        return fn(*args, **kwargs)

    def claim_once(key, *, ttl_seconds):
        if key in claimed:
            return False
        claimed.add(key)
        return True

    def cache_delete(key):
        claimed.discard(key)
        return True

    from agent.aegra import redis as redis_module

    monkeypatch.setattr(redis_module, "run_redis", run_redis)
    monkeypatch.setattr(redis_module, "claim_once", claim_once)
    monkeypatch.setattr(redis_module, "cache_delete", cache_delete)
    return claimed


@pytest.fixture
def webhook(monkeypatch):
    tally = {"posts": 0}

    def set_up(status):
        import httpx

        import agent.src.knowledge.fetch as fetch

        monkeypatch.setattr(fetch, "assert_safe_url", lambda _url: None)

        class FakeClient:
            def __init__(self, *_a, **_k): ...
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_a):
                return False

            async def post(self, *_a, **_k):
                tally["posts"] += 1
                if isinstance(status, Exception):
                    raise status
                return httpx.Response(status, request=httpx.Request("POST", "http://x"))

        monkeypatch.setattr(dispatch.httpx, "AsyncClient", FakeClient)
        return tally

    return set_up


class TestASecondPodDoesNotResend:
    @pytest.mark.asyncio
    async def test_the_claim_is_shared(self, webhook, shared_redis):
        tally = webhook(200)
        await dispatch.deliver("the answer", _message(), Channel())

        dispatch._DELIVERED.clear()
        await dispatch.deliver("the answer", _message(), Channel())

        assert tally["posts"] == 1, (
            "the second pod had no memory of the delivery and sent it again"
        )

    @pytest.mark.asyncio
    async def test_a_different_answer_still_goes(self, webhook, shared_redis):
        tally = webhook(200)
        await dispatch.deliver("one", _message(), Channel())
        await dispatch.deliver("two", _message(), Channel())
        assert tally["posts"] == 2


class TestAFailedDeliveryReleasesTheClaim:
    @pytest.mark.asyncio
    async def test_another_pod_may_still_try(self, webhook, shared_redis):
        """Otherwise the claim is worse than the dict it replaced."""
        import httpx

        tally = webhook(httpx.ConnectTimeout("too slow"))
        await dispatch.deliver("the answer", _message(), Channel())
        dispatch._DELIVERED.clear()
        await dispatch.deliver("the answer", _message(), Channel())
        assert tally["posts"] == 2


class TestRedisDownFallsBackRatherThanRefusing:
    @pytest.mark.asyncio
    async def test_the_local_memory_decides(self, webhook, monkeypatch):
        async def run_redis(fn, /, *args, **kwargs):
            return None

        from agent.aegra import redis as redis_module

        monkeypatch.setattr(redis_module, "run_redis", run_redis)

        tally = webhook(200)
        await dispatch.deliver("the answer", _message(), Channel())
        await dispatch.deliver("the answer", _message(), Channel())
        assert tally["posts"] == 1
