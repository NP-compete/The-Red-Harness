"""A Redis that is down costs one attempt, not one per call (REL-3)."""

from __future__ import annotations

import pytest

from agent.aegra import redis as redis_module


@pytest.fixture(autouse=True)
def forget():
    redis_module._client = None
    redis_module._unavailable_until = 0.0
    yield
    redis_module._client = None
    redis_module._unavailable_until = 0.0


@pytest.fixture
def refusing(monkeypatch):
    """A Redis that cannot be reached, counting the attempts."""
    tally = {"attempts": 0}

    class FakeRedis:
        @staticmethod
        def from_url(*_a, **_k):
            tally["attempts"] += 1
            raise ConnectionError("Connection refused")

    monkeypatch.setitem(__import__("sys").modules, "redis", FakeRedis)
    return tally


class TestTheFailureIsRemembered:
    def test_a_hundred_calls_make_one_attempt(self, refusing):
        for _ in range(100):
            assert redis_module.get_redis_client() is None
        assert refusing["attempts"] == 1, (
            f"{refusing['attempts']} connection attempts for 100 calls — a "
            "down Redis costs a socket timeout each time, which is the "
            "cascade rather than the degradation"
        )

    def test_it_tries_again_after_the_cool_off(self, refusing, monkeypatch):
        """A Redis that comes back must be picked up."""
        redis_module.get_redis_client()
        assert refusing["attempts"] == 1

        now = redis_module.time.monotonic()
        monkeypatch.setattr(
            redis_module.time,
            "monotonic",
            lambda: now + redis_module._UNAVAILABLE_FOR_SECONDS + 1,
        )
        redis_module.get_redis_client()
        assert refusing["attempts"] == 2

    def test_the_cool_off_is_short(self):
        assert 1.0 <= redis_module._UNAVAILABLE_FOR_SECONDS <= 30.0


class TestASuccessIsStillCached:
    def test_the_client_is_reused(self, monkeypatch):
        tally = {"attempts": 0}

        class Client:
            def ping(self):
                return True

        class FakeRedis:
            @staticmethod
            def from_url(*_a, **_k):
                tally["attempts"] += 1
                return Client()

        monkeypatch.setitem(__import__("sys").modules, "redis", FakeRedis)
        first = redis_module.get_redis_client()
        for _ in range(10):
            assert redis_module.get_redis_client() is first
        assert tally["attempts"] == 1


class TestTheClaimAndTheReleaseAgreeOnTheKey:
    """They did not, and only the cluster could tell me."""

    def test_both_touch_the_same_key(self, monkeypatch):
        touched: list[str] = []

        class Client:
            def set(self, key, *_a, **_k):
                touched.append(key)
                return True

            def delete(self, key):
                touched.append(key)
                return 1

            def ping(self):
                return True

        monkeypatch.setattr(redis_module, "_client", Client())
        redis_module.claim_once("channel:sent:abc", ttl_seconds=60)
        redis_module.cache_delete("channel:sent:abc")

        assert touched[0] == touched[1], (
            f"the claim wrote {touched[0]!r} and the release removed "
            f"{touched[1]!r} — the claim is never released"
        )

    def test_the_key_carries_the_deployment_prefix(self, monkeypatch):
        touched: list[str] = []

        class Client:
            def set(self, key, *_a, **_k):
                touched.append(key)
                return True

            def ping(self):
                return True

        monkeypatch.setattr(redis_module, "_client", Client())
        redis_module.claim_once("channel:sent:abc", ttl_seconds=60)
        assert touched[0].startswith(redis_module.REDIS_KEY_PREFIX)
