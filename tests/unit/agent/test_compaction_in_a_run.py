"""Shortening a conversation that has grown too long, in a run."""

from __future__ import annotations

import pytest

from agent.src.agent.compaction import Message, can_be_wired, shorten


def _long(count=12, tokens=100):
    out = []
    for i in range(count):
        out.append(Message(role="user", text=f"question {i}", tokens=tokens))
        out.append(Message(role="assistant", text=f"answer {i}", tokens=tokens))
    return out


async def _summarise(messages):
    return f"Earlier: {len(messages)} messages."


class TestWhenItFires:
    @pytest.mark.asyncio
    async def test_a_short_conversation_is_left_alone(self):
        short = _long(count=1)
        assert await shorten(short, limit_tokens=10_000, summarise=_summarise) is short

    @pytest.mark.asyncio
    async def test_a_long_one_is_shortened(self):
        long = _long()
        found = await shorten(long, limit_tokens=1_000, summarise=_summarise)
        assert len(found) < len(long)

    @pytest.mark.asyncio
    async def test_the_recent_turns_survive_verbatim(self):
        long = _long()
        found = await shorten(long, limit_tokens=1_000, summarise=_summarise)
        assert found[-1].text == long[-1].text

    @pytest.mark.asyncio
    async def test_the_summary_stands_where_the_messages_were(self):
        long = _long()
        found = await shorten(long, limit_tokens=1_000, summarise=_summarise)
        assert any(m.is_summary for m in found)


class TestWhenAnythingGoesWrong:
    @pytest.mark.asyncio
    async def test_a_summariser_that_fails_leaves_the_history_alone(self):
        async def _broken(messages):
            raise ConnectionError("model unavailable")

        long = _long()
        assert await shorten(long, limit_tokens=1_000, summarise=_broken) is long

    @pytest.mark.asyncio
    async def test_an_empty_summary_leaves_it_alone_too(self):
        async def _nothing(messages):
            return "   "

        long = _long()
        assert await shorten(long, limit_tokens=1_000, summarise=_nothing) is long

    @pytest.mark.asyncio
    async def test_a_summariser_that_hangs_is_not_waited_on_forever(self):
        import asyncio

        async def _slow(messages):
            await asyncio.sleep(10)
            return "late"

        long = _long()
        found = await shorten(
            long, limit_tokens=1_000, summarise=_slow, timeout_seconds=0.05
        )
        assert found is long


class TestWhatIsNeverSummarisedAway:
    @pytest.mark.asyncio
    async def test_a_pending_approval_stays(self):
        long = _long()
        long[0] = Message(
            role="assistant", text="may I?", tokens=100, awaiting_approval=True
        )
        found = await shorten(long, limit_tokens=1_000, summarise=_summarise)
        assert any(m.awaiting_approval for m in found)

    @pytest.mark.asyncio
    async def test_the_system_prompt_stays(self):
        long = _long()
        long.insert(0, Message(role="system", text="you are", tokens=100))
        found = await shorten(long, limit_tokens=1_000, summarise=_summarise)
        assert any(m.role == "system" for m in found)


class TestTrustTravels:
    @pytest.mark.asyncio
    async def test_a_summary_of_untrusted_content_is_untrusted(self):
        long = _long()
        long[0] = Message(
            role="user", text="from a web page", tokens=100, trusted=False
        )
        found = await shorten(long, limit_tokens=1_000, summarise=_summarise)
        summary = next(m for m in found if m.is_summary)
        assert summary.trusted is False

    @pytest.mark.asyncio
    async def test_a_summary_of_trusted_content_stays_trusted(self):
        found = await shorten(_long(), limit_tokens=1_000, summarise=_summarise)
        summary = next(m for m in found if m.is_summary)
        assert summary.trusted is True


class TestItIsNotWiredYetAndSaysSo:
    """A stub that runs and compacts nothing would be worse"""

    def test_it_reports_that_it_cannot_be_wired(self):
        wired, _reason = can_be_wired()
        assert wired is False

    def test_the_reason_names_what_is_missing(self):
        _wired, reason = can_be_wired()
        for flag in ("awaiting_approval", "is_skill", "trusted"):
            assert flag in reason

    def test_the_reason_says_why_guessing_is_not_an_option(self):
        _wired, reason = can_be_wired()
        assert "guessing" in reason
