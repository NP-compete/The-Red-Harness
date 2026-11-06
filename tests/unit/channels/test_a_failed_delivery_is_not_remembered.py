"""A delivery that did not arrive is not recorded as one (REL-3)."""

from __future__ import annotations

import httpx
import pytest

from agent.src.channels import dispatch


class Channel:
    def __init__(self, type_: str = "webhook"):
        self.type = type_


def _message(**over):
    class Message:
        conversation = "C1"
        reply_to = "https://example.test/callback"
        metadata: dict = {}

    said = Message()
    for key, value in over.items():
        setattr(said, key, value)
    return said


@pytest.fixture(autouse=True)
def forget():
    dispatch._DELIVERED.clear()
    yield
    dispatch._DELIVERED.clear()


@pytest.fixture
def webhook(monkeypatch):
    """Make the callback do what the test says, and count attempts."""
    tally = {"posts": 0}

    def set_up(answer):
        async def safe(_url):
            return None

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
                if isinstance(answer, Exception):
                    raise answer
                return httpx.Response(answer, request=httpx.Request("POST", "http://x"))

        monkeypatch.setattr(dispatch.httpx, "AsyncClient", FakeClient)
        return tally

    return set_up


async def _deliver(message=None):
    await dispatch.deliver("the answer", message or _message(), Channel())


class TestAFailureLeavesTheDoorOpen:
    @pytest.mark.asyncio
    async def test_a_callback_that_times_out_is_retried(self, webhook):
        tally = webhook(httpx.ConnectTimeout("too slow"))
        await _deliver()
        await _deliver()
        assert tally["posts"] == 2, (
            "the second attempt was suppressed as a duplicate of a delivery "
            "that never arrived"
        )

    @pytest.mark.asyncio
    async def test_a_callback_answering_500_is_retried(self, webhook):
        tally = webhook(500)
        await _deliver()
        await _deliver()
        assert tally["posts"] == 2

    @pytest.mark.asyncio
    async def test_it_does_not_raise(self, webhook):
        """The other half of the clause, and it was already right."""
        webhook(httpx.ConnectTimeout("too slow"))
        await _deliver()


class TestASuccessIsStillRememberedOnce:
    @pytest.mark.asyncio
    async def test_the_same_answer_is_not_sent_twice(self, webhook):
        tally = webhook(200)
        await _deliver()
        await _deliver()
        assert tally["posts"] == 1

    @pytest.mark.asyncio
    async def test_a_different_answer_still_goes(self, webhook):
        tally = webhook(200)
        await _deliver()
        await dispatch.deliver("a different answer", _message(), Channel())
        assert tally["posts"] == 2


class TestNowhereToSendIt:
    @pytest.mark.asyncio
    async def test_no_reply_address_remembers_nothing(self, webhook):
        """A channel that later gains one should deliver."""
        tally = webhook(200)
        await _deliver(_message(reply_to=None))
        assert tally["posts"] == 0
        await _deliver()
        assert tally["posts"] == 1
