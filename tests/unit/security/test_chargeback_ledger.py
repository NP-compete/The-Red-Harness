"""What a month cost, and who should be billed for it."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.security.cost_attribution import (
    RunCost,
    charge_for,
    charges_in,
    month_of,
)


class _Redis:
    def __init__(self, values=None):
        self.hashes: dict[str, dict[str, str]] = dict(values or {})
        self.expired: list[tuple[str, int]] = []
        self.numbers: dict[str, int] = {}

    async def incr(self, key):
        self.numbers[key] = self.numbers.get(key, 0) + 1
        return self.numbers[key]

    async def get(self, key):
        return self.numbers.get(key)

    async def hincrbyfloat(self, key, field, amount):
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = str(float(bucket.get(field, 0)) + amount)

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def expire(self, key, seconds):
        self.expired.append((key, seconds))


def _run(**kwargs):
    return RunCost(
        run_id=kwargs.pop("run_id", "run-1"),
        person=kwargs.pop("person", "alice"),
        team=kwargs.pop("team", ""),
        project=kwargs.pop("project", ""),
        amount=kwargs.pop("amount", Decimal("1.25")),
        **kwargs,
    )


class TestTheMonthKey:
    def test_it_is_a_calendar_month(self):
        assert month_of("2026-03-04") == "2026-03"

    def test_it_is_not_a_day(self):
        assert month_of("2026-03-04") != "2026-03-04"


class TestWritingACharge:
    @pytest.mark.asyncio
    async def test_a_run_lands_on_its_payer(self):
        redis = _Redis()
        await charge_for(_run(), client=redis, month="2026-03")
        assert (await charges_in("2026-03", client=redis))["alice"][
            "amount"
        ] == Decimal("1.25")

    @pytest.mark.asyncio
    async def test_a_team_run_is_billed_to_the_team(self):
        redis = _Redis()
        await charge_for(_run(team="platform"), client=redis, month="2026-03")
        found = await charges_in("2026-03", client=redis)
        assert set(found) == {"platform"}

    @pytest.mark.asyncio
    async def test_two_runs_on_one_payer_add_up(self):
        redis = _Redis()
        await charge_for(_run(amount=Decimal("1.25")), client=redis, month="2026-03")
        await charge_for(_run(amount=Decimal("2.75")), client=redis, month="2026-03")
        found = await charges_in("2026-03", client=redis)
        assert found["alice"]["amount"] == Decimal("4.00")

    @pytest.mark.asyncio
    async def test_the_number_of_runs_is_counted_too(self):
        redis = _Redis()
        await charge_for(_run(), client=redis, month="2026-03")
        await charge_for(_run(), client=redis, month="2026-03")
        found = await charges_in("2026-03", client=redis)
        assert found["alice"]["runs"] == 2

    @pytest.mark.asyncio
    async def test_payers_are_kept_apart(self):
        redis = _Redis()
        await charge_for(_run(person="alice"), client=redis, month="2026-03")
        await charge_for(_run(person="bob"), client=redis, month="2026-03")
        assert set(await charges_in("2026-03", client=redis)) == {"alice", "bob"}

    @pytest.mark.asyncio
    async def test_months_are_kept_apart(self):
        redis = _Redis()
        await charge_for(_run(), client=redis, month="2026-03")
        assert await charges_in("2026-04", client=redis) == {}

    @pytest.mark.asyncio
    async def test_a_month_is_kept_long_enough_to_be_billed(self):
        redis = _Redis()
        await charge_for(_run(), client=redis, month="2026-03")
        assert redis.expired and all(
            seconds > 60 * 24 * 60 * 60 for _key, seconds in redis.expired
        )


class TestNothingToCharge:
    @pytest.mark.asyncio
    async def test_a_run_that_cost_nothing_is_not_written(self):
        redis = _Redis()
        await charge_for(_run(amount=Decimal("0")), client=redis, month="2026-03")
        assert await charges_in("2026-03", client=redis) == {}

    @pytest.mark.asyncio
    async def test_a_ledger_that_cannot_be_written_does_not_lose_the_answer(self):
        class _Broken:
            async def hincrbyfloat(self, key, field, amount):
                raise RuntimeError("redis is down")

            async def expire(self, key, seconds):
                raise RuntimeError("redis is down")

        await charge_for(_run(), client=_Broken(), month="2026-03")

    @pytest.mark.asyncio
    async def test_a_ledger_that_cannot_be_read_is_empty_rather_than_an_error(self):
        class _Broken:
            async def hgetall(self, key):
                raise RuntimeError("redis is down")

        assert await charges_in("2026-03", client=_Broken()) == {}

    @pytest.mark.asyncio
    async def test_a_figure_that_is_not_an_amount_is_skipped(self):
        redis = _Redis({"charge:2026-03": {"alice": "1.25", "bob": "soon"}})
        found = await charges_in("2026-03", client=redis)
        assert set(found) == {"alice"}


class TestARunNobodyCouldPrice:
    """A total beside unpriced runs reads as complete when it is not."""

    @pytest.mark.asyncio
    async def test_it_is_counted_rather_than_dropped(self):
        from agent.src.security.cost_attribution import unpriced_in

        redis = _Redis()
        redis.numbers = {}
        await charge_for(_run(amount=Decimal("0")), client=redis, month="2026-03")
        assert await unpriced_in("2026-03", client=redis) == 1

    @pytest.mark.asyncio
    async def test_it_does_not_reach_the_invoice(self):
        """Counted is not charged: nobody owes money for a run"""
        redis = _Redis()
        redis.numbers = {}
        await charge_for(_run(amount=Decimal("0")), client=redis, month="2026-03")
        assert await charges_in("2026-03", client=redis) == {}

    @pytest.mark.asyncio
    async def test_a_month_with_none_says_zero(self):
        from agent.src.security.cost_attribution import unpriced_in

        redis = _Redis()
        redis.numbers = {}
        assert await unpriced_in("2026-03", client=redis) == 0

    @pytest.mark.asyncio
    async def test_a_broken_counter_does_not_break_the_invoice(self):
        """The bill is the record; the count beside it is a"""

        class _NoCounter(_Redis):
            async def incr(self, key):
                raise RuntimeError("no")

        redis = _NoCounter()
        await charge_for(_run(amount=Decimal("0")), client=redis, month="2026-03")
        await charge_for(_run(), client=redis, month="2026-03")
        assert (await charges_in("2026-03", client=redis))["alice"][
            "amount"
        ] == Decimal("1.25")
