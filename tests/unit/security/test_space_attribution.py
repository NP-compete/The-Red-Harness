"""E33-T5. What a room cost, and which of us spent it."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.security.cost_attribution import (
    RunCost,
    attribute,
    charge_for,
    charges_in,
    space_charges_in,
)


class _Redis:
    def __init__(self):
        self.hashes: dict[str, dict[str, str]] = {}

    async def hincrbyfloat(self, key, field, amount):
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = str(float(bucket.get(field, 0)) + amount)

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def expire(self, key, seconds):
        pass


class _BrokenOnSpaces(_Redis):
    """Writes the invoice, then fails on the room's view."""

    async def hincrbyfloat(self, key, field, amount):
        if ":space:" in key:
            raise RuntimeError("no")
        await super().hincrbyfloat(key, field, amount)


def _run(**kwargs):
    return RunCost(
        run_id=kwargs.pop("run_id", "run-1"),
        person=kwargs.pop("person", "alice"),
        team=kwargs.pop("team", ""),
        project=kwargs.pop("project", ""),
        amount=kwargs.pop("amount", Decimal("1.25")),
        **kwargs,
    )


class TestASpaceIsNotAPayer:
    def test_the_room_does_not_become_the_payer(self):
        """Nobody receives an invoice addressed to a chat room."""
        charged = attribute(_run(space="room-1"))
        assert charged.charged_to == "alice"
        assert charged.space == "room-1"

    def test_a_project_still_pays_before_a_person_in_a_room(self):
        assert attribute(_run(space="room-1", project="apollo")).charged_to == "apollo"

    @pytest.mark.asyncio
    async def test_a_run_in_a_room_is_billed_once(self):
        redis = _Redis()
        await charge_for(_run(space="room-1"), client=redis, month="2026-03")
        payers = await charges_in("2026-03", client=redis)
        assert payers["alice"]["amount"] == Decimal("1.25")
        assert payers["alice"]["runs"] == 1
        assert "room-1" not in payers


class TestTheRoomsView:
    @pytest.mark.asyncio
    async def test_it_is_kept_per_person(self):
        redis = _Redis()
        for person, amount in (("alice", "0.40"), ("bo", "1.10"), ("alice", "0.20")):
            await charge_for(
                _run(person=person, amount=Decimal(amount), space="room-1"),
                client=redis,
                month="2026-03",
            )
        rows = await space_charges_in("room-1", "2026-03", client=redis)
        assert rows["alice"] == {"amount": Decimal("0.60"), "runs": 2}
        assert rows["bo"] == {"amount": Decimal("1.10"), "runs": 1}

    @pytest.mark.asyncio
    async def test_a_run_outside_a_room_is_not_in_any_room(self):
        redis = _Redis()
        await charge_for(_run(amount=Decimal("9.99")), client=redis, month="2026-03")
        assert await space_charges_in("room-1", "2026-03", client=redis) == {}

    @pytest.mark.asyncio
    async def test_one_room_does_not_see_another(self):
        redis = _Redis()
        await charge_for(_run(space="room-1"), client=redis, month="2026-03")
        assert await space_charges_in("room-2", "2026-03", client=redis) == {}

    @pytest.mark.asyncio
    async def test_a_month_is_its_own_ledger(self):
        redis = _Redis()
        await charge_for(_run(space="room-1"), client=redis, month="2026-03")
        assert await space_charges_in("room-1", "2026-04", client=redis) == {}

    @pytest.mark.asyncio
    async def test_losing_the_rooms_view_does_not_lose_the_invoice(self):
        """The bill is the thing that must survive."""
        redis = _BrokenOnSpaces()
        await charge_for(_run(space="room-1"), client=redis, month="2026-03")
        assert (await charges_in("2026-03", client=redis))["alice"][
            "amount"
        ] == Decimal("1.25")
        assert await space_charges_in("room-1", "2026-03", client=redis) == {}


class TestWhereTheRoomComesFrom:
    def test_a_run_says_which_room_it_ran_in(self):
        from agent.src.infrastructure.backend import attribution_from_runtime

        class _Runtime:
            config = {"metadata": {"space_id": "room-1"}}

        assert attribution_from_runtime(_Runtime())["space"] == "room-1"

    def test_a_run_outside_a_room_says_so_rather_than_guessing(self):
        from agent.src.infrastructure.backend import attribution_from_runtime

        class _Runtime:
            config = {"metadata": {}}

        assert attribution_from_runtime(_Runtime())["space"] == ""
