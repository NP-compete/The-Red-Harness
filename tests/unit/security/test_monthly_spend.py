"""What a caller has spent this month, as well as today."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.security.caller_spend import (
    month_key_for,
    record,
    spent_this_month,
    this_month,
)


class _Redis:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.added: list[tuple[str, float]] = []
        self.expired: list[tuple[str, int]] = []

    async def get(self, key):
        return self.values.get(key)

    async def incrbyfloat(self, key, amount):
        self.added.append((key, amount))
        self.values[key] = str(float(self.values.get(key, 0)) + amount)

    async def expire(self, key, seconds):
        self.expired.append((key, seconds))


class TestTheMonthKey:
    def test_it_names_the_month(self):
        assert "2026-03" in month_key_for("alice", month="2026-03")

    def test_it_names_the_caller(self):
        assert "alice" in month_key_for("alice", month="2026-03")

    def test_it_is_not_the_same_key_as_a_day(self):
        from agent.src.security.caller_spend import key_for

        assert month_key_for("alice", month="2026-03") != key_for(
            "alice", day="2026-03"
        )

    def test_the_month_is_in_utc(self):
        assert len(this_month()) == len("2026-03")


class TestReadingTheMonth:
    @pytest.mark.asyncio
    async def test_a_caller_who_has_spent_nothing_has_spent_nothing(self):
        found = await spent_this_month("alice", client=_Redis(), month="2026-03")
        assert found == Decimal("0")

    @pytest.mark.asyncio
    async def test_it_reads_what_was_counted(self):
        redis = _Redis({month_key_for("alice", month="2026-03"): "12.50"})
        found = await spent_this_month(
            "alice", client=_Redis(redis.values), month="2026-03"
        )
        assert found == Decimal("12.50")

    @pytest.mark.asyncio
    async def test_a_counter_that_is_down_reads_as_nothing(self):
        class _Broken:
            async def get(self, key):
                raise RuntimeError("redis is down")

        assert await spent_this_month("alice", client=_Broken()) == Decimal("0")

    @pytest.mark.asyncio
    async def test_an_unnamed_caller_has_spent_nothing(self):
        assert await spent_this_month("", client=_Redis()) == Decimal("0")


class TestRecording:
    @pytest.mark.asyncio
    async def test_the_month_is_counted_too(self):
        redis = _Redis()
        await record("alice", Decimal("1.25"), client=redis, day="2026-03-04")
        assert any(
            month_key_for("alice", month="2026-03") == key for key, _ in redis.added
        )

    @pytest.mark.asyncio
    async def test_the_day_is_still_counted(self):
        from agent.src.security.caller_spend import key_for

        redis = _Redis()
        await record("alice", Decimal("1.25"), client=redis, day="2026-03-04")
        assert any(key_for("alice", day="2026-03-04") == key for key, _ in redis.added)

    @pytest.mark.asyncio
    async def test_the_month_key_is_given_an_expiry(self):
        redis = _Redis()
        await record("alice", Decimal("1.25"), client=redis, day="2026-03-04")
        assert any(
            key == month_key_for("alice", month="2026-03") for key, _ in redis.expired
        )

    @pytest.mark.asyncio
    async def test_the_month_outlives_the_day(self):
        redis = _Redis()
        await record("alice", Decimal("1.25"), client=redis, day="2026-03-04")
        kept = dict(redis.expired)
        assert (
            kept[month_key_for("alice", month="2026-03")]
            > kept[[key for key in kept if "month" not in key][0]]
        )

    @pytest.mark.asyncio
    async def test_a_month_that_cannot_be_counted_does_not_lose_the_answer(self):
        class _Broken:
            async def incrbyfloat(self, key, amount):
                raise RuntimeError("redis is down")

            async def expire(self, key, seconds):
                raise RuntimeError("redis is down")

        await record("alice", Decimal("1.25"), client=_Broken())

    @pytest.mark.asyncio
    async def test_nothing_spent_is_not_recorded(self):
        redis = _Redis()
        await record("alice", Decimal("0"), client=redis)
        assert redis.added == []
