"""What a caller has spent today, counted somewhere every pod sees."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.security.caller_spend import key_for, record, spent_today


class _Redis:
    """Enough of the client to tell whether it was used correctly."""

    def __init__(self, values=None):
        self.values = dict(values or {})
        self.expires: dict[str, int] = {}

    async def get(self, key):
        return self.values.get(key)

    async def incrbyfloat(self, key, amount):
        self.values[key] = float(self.values.get(key, 0)) + float(amount)
        return self.values[key]

    async def expire(self, key, seconds):
        self.expires[key] = seconds
        return True


class TestTheKey:
    def test_it_carries_the_caller(self):
        assert "svc-a" in key_for("svc-a", day="2026-10-28")

    def test_it_carries_the_day(self):
        assert "2026-10-28" in key_for("svc-a", day="2026-10-28")

    def test_two_callers_do_not_share_one(self):
        assert key_for("svc-a", day="d") != key_for("svc-b", day="d")

    def test_two_days_do_not_share_one(self):
        assert key_for("svc-a", day="d1") != key_for("svc-a", day="d2")


class TestReadingIt:
    @pytest.mark.asyncio
    async def test_a_caller_that_has_spent_nothing_reads_zero(self):
        found = await spent_today("svc-a", client=_Redis(), day="d")
        assert found == Decimal("0")

    @pytest.mark.asyncio
    async def test_what_was_recorded_comes_back(self):
        redis = _Redis({key_for("svc-a", day="d"): "1.25"})
        assert await spent_today(
            "svc-a", client=_Redis({**redis.values}), day="d"
        ) == Decimal("1.25")

    @pytest.mark.asyncio
    async def test_it_comes_back_as_a_decimal(self):
        redis = _Redis({key_for("svc-a", day="d"): "0.1"})
        assert isinstance(await spent_today("svc-a", client=redis, day="d"), Decimal)

    @pytest.mark.asyncio
    async def test_a_value_nobody_can_read_counts_as_nothing(self):
        redis = _Redis({key_for("svc-a", day="d"): "not a number"})
        assert await spent_today("svc-a", client=redis, day="d") == Decimal("0")

    @pytest.mark.asyncio
    async def test_a_store_that_is_down_counts_as_nothing(self):
        class _Down:
            async def get(self, key):
                raise ConnectionError("no redis")

        assert await spent_today("svc-a", client=_Down(), day="d") == Decimal("0")


class TestRecordingIt:
    @pytest.mark.asyncio
    async def test_an_amount_is_added(self):
        redis = _Redis()
        await record("svc-a", Decimal("0.50"), client=redis, day="d")
        assert await spent_today("svc-a", client=redis, day="d") == Decimal("0.5")

    @pytest.mark.asyncio
    async def test_amounts_accumulate(self):
        redis = _Redis()
        await record("svc-a", Decimal("0.50"), client=redis, day="d")
        await record("svc-a", Decimal("0.25"), client=redis, day="d")
        assert await spent_today("svc-a", client=redis, day="d") == Decimal("0.75")

    @pytest.mark.asyncio
    async def test_the_counter_is_given_an_expiry(self):
        redis = _Redis()
        await record("svc-a", Decimal("1"), client=redis, day="d")
        assert redis.expires[key_for("svc-a", day="d")] > 0

    @pytest.mark.asyncio
    async def test_nothing_is_recorded_for_nothing_spent(self):
        redis = _Redis()
        await record("svc-a", Decimal("0"), client=redis, day="d")
        assert redis.values == {}

    @pytest.mark.asyncio
    async def test_a_store_that_is_down_does_not_fail_the_run(self):
        class _Down:
            async def incrbyfloat(self, key, amount):
                raise ConnectionError("no redis")

        await record("svc-a", Decimal("1"), client=_Down(), day="d")

    @pytest.mark.asyncio
    async def test_a_caller_with_no_name_is_not_counted(self):
        redis = _Redis()
        await record("", Decimal("1"), client=redis, day="d")
        assert redis.values == {}


class TestTheRunReportsWhatItSpent:
    """The counter is only a cap if something increments it."""

    @pytest.mark.asyncio
    async def test_what_a_run_spent_is_recorded_against_its_caller(self):
        from agent.src.security.spend_middleware import SpendLimitMiddleware

        said: list[tuple[str, Decimal]] = []

        async def _record(caller, amount, *, context=None):
            said.append((caller, amount))

        mw = SpendLimitMiddleware(on_spent=_record)
        mw.spent = Decimal("0.40")
        await mw.aafter_agent({}, _runtime("svc-a"))
        assert said == [("svc-a", Decimal("0.40"))]

    @pytest.mark.asyncio
    async def test_a_run_that_spent_nothing_records_nothing(self):
        from agent.src.security.spend_middleware import SpendLimitMiddleware

        said = []

        async def _record(caller, amount, *, context=None):
            said.append((caller, amount))

        mw = SpendLimitMiddleware(on_spent=_record)
        await mw.aafter_agent({}, _runtime("svc-a"))
        assert said == []

    @pytest.mark.asyncio
    async def test_a_run_with_no_identifiable_caller_records_nothing(self):
        from agent.src.security.spend_middleware import SpendLimitMiddleware

        said = []

        async def _record(caller, amount, *, context=None):
            said.append((caller, amount))

        mw = SpendLimitMiddleware(on_spent=_record)
        mw.spent = Decimal("1")
        await mw.aafter_agent({}, _runtime(None))
        assert said == []

    @pytest.mark.asyncio
    async def test_a_recorder_that_fails_does_not_fail_the_run(self):
        from agent.src.security.spend_middleware import SpendLimitMiddleware

        async def _broken(caller, amount):
            raise ConnectionError("no redis")

        mw = SpendLimitMiddleware(on_spent=_broken)
        mw.spent = Decimal("1")
        await mw.aafter_agent({}, _runtime("svc-a"))

    @pytest.mark.asyncio
    async def test_nothing_is_recorded_when_no_recorder_is_wired(self):
        from agent.src.security.spend_middleware import SpendLimitMiddleware

        mw = SpendLimitMiddleware()
        mw.spent = Decimal("1")
        await mw.aafter_agent({}, _runtime("svc-a"))


class _runtime:
    def __init__(self, user_id):
        self.config = {"metadata": {"user_id": user_id}} if user_id else {}
