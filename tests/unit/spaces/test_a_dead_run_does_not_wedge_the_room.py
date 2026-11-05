"""The room's run slot frees itself (REL-4)."""

from __future__ import annotations

import pytest

from agent.src.spaces import store


class FakeCursor:
    def __init__(self, row):
        self._row = row

    async def fetchone(self):
        return self._row


class FakeConnection:
    """Records what was asked, and answers whatever it was told to."""

    def __init__(self, rows):
        self.rows = list(rows)
        self.statements: list[tuple[str, tuple]] = []

    async def execute(self, sql, params=()):
        self.statements.append((" ".join(sql.split()), params))
        return FakeCursor(self.rows.pop(0) if self.rows else None)


@pytest.fixture
def claim(monkeypatch):
    from contextlib import asynccontextmanager

    async def nothing():
        return None

    monkeypatch.setattr(store, "_ensure_table", nothing)

    async def run(rows) -> tuple[FakeConnection, object]:
        conn = FakeConnection(rows)

        @asynccontextmanager
        async def connection():
            yield conn

        import agent.src.db.pool as pool

        monkeypatch.setattr(pool, "connection", connection)
        try:
            taken = await store.claim_run("s1", run_id="r2", by="bob")
        except store.SpaceBusy as refused:
            return conn, refused
        return conn, taken

    return run


class TestTheClaimLetsGoOfAStaleSlot:
    @pytest.mark.asyncio
    async def test_the_age_of_the_claim_is_part_of_the_condition(self, claim):
        conn, _ = await claim(
            [{"active_run_id": "r2", "active_run_by": "bob", "active_run_at": "now"}]
        )
        sql, params = conn.statements[0]
        assert "active_run_at <" in sql, (
            "the claim is conditional on the slot being empty and nothing "
            "else, so a run that died holds the room for ever"
        )
        assert store.STALE_RUN_AFTER_SECONDS in params

    @pytest.mark.asyncio
    async def test_an_empty_slot_is_still_taken(self, claim):
        _, taken = await claim(
            [{"active_run_id": "r2", "active_run_by": "bob", "active_run_at": "now"}]
        )
        assert taken.run_id == "r2"

    @pytest.mark.asyncio
    async def test_a_live_claim_is_still_refused(self, claim):
        """The guard has to look both ways."""
        _, refused = await claim([None, {"active_run_by": "ada"}])
        assert isinstance(refused, store.SpaceBusy)
        assert refused.holder == "ada"

    @pytest.mark.asyncio
    async def test_the_refusal_says_the_room_frees_itself(self, claim):
        _, refused = await claim([None, {"active_run_by": "ada"}])
        assert "frees itself" in str(refused)
        assert str(store.STALE_RUN_AFTER_SECONDS // 60) in str(refused)


class TestTheWindow:
    def test_it_is_above_any_run_this_product_expects(self):
        assert 5 * 60 <= store.STALE_RUN_AFTER_SECONDS <= 60 * 60
