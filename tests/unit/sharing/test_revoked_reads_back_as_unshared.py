"""A revoked link reads back as not shared."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from agent.aegra import share_routes
from agent.src.sharing.store import Share


def _share(**over) -> Share:
    made = {
        "share_id": "s1",
        "thread_id": "t1",
        "owner_id": "ada",
        "title": "Travel limits",
        "scope": "authenticated",
        "created_at": datetime.now(UTC) - timedelta(days=1),
        "expires_at": None,
        "revoked_at": None,
        "views": 0,
        "last_viewed_at": None,
    }
    made.update(over)
    return Share(**made)


@pytest.fixture
def answer(monkeypatch):
    async def read(share):
        async def get_share_for_thread(thread_id, user_id):
            return share

        async def who(request, reject_anonymous=False):
            return "ada"

        monkeypatch.setattr(
            share_routes.store, "get_share_for_thread", get_share_for_thread
        )
        monkeypatch.setattr(share_routes, "authenticated_user_id", who)
        return await share_routes.get_thread_share("t1", object())

    return read


class TestWhatSharedMeans:
    @pytest.mark.asyncio
    async def test_a_live_link_is_shared(self, answer):
        said = await answer(_share())
        assert said["shared"] is True

    @pytest.mark.asyncio
    async def test_a_revoked_link_is_not(self, answer):
        said = await answer(_share(revoked_at=datetime.now(UTC)))
        assert said["shared"] is False, (
            "the owner revoked the link and the conversation still reports "
            "itself as shared"
        )

    @pytest.mark.asyncio
    async def test_a_lapsed_link_is_not(self, answer):
        said = await answer(_share(expires_at=datetime.now(UTC) - timedelta(days=1)))
        assert said["shared"] is False

    @pytest.mark.asyncio
    async def test_never_shared_says_so_and_nothing_else(self, answer):
        said = await answer(None)
        assert said == {"shared": False}


class TestTheRowIsStillThere:
    """`shared: false` must not mean "I lost the share"."""

    @pytest.mark.asyncio
    async def test_the_reason_the_link_is_dead_survives(self, answer):
        said = await answer(_share(revoked_at=datetime.now(UTC)))
        assert said["share_id"] == "s1"
        assert said["revoked_at"]
        assert said["active"] is False


class TestADeadLinkSaysWhichKindOfDead:
    """410, and an `error` code a client can switch on (MU-4)."""

    @pytest.fixture
    def read(self, monkeypatch):
        async def go(share):
            async def read_share(_share_id):
                return share, {"captured_at": None, "messages": []}

            async def who(request, reject_anonymous=False):
                return "ada"

            monkeypatch.setattr(share_routes.store, "read_share", read_share)
            monkeypatch.setattr(share_routes, "authenticated_user_id", who)
            return await share_routes.read_shared("s1", object())

        return go

    @pytest.mark.asyncio
    async def test_an_expired_link(self, read):
        import json

        answer = await read(_share(expires_at=datetime.now(UTC) - timedelta(days=1)))
        assert answer.status_code == 410
        body = json.loads(answer.body)
        assert body["error"] == "expired"
        assert "expired" in body["message"]

    @pytest.mark.asyncio
    async def test_a_revoked_link_is_not_the_same_answer(self, read):
        import json

        answer = await read(_share(revoked_at=datetime.now(UTC)))
        assert answer.status_code == 410
        body = json.loads(answer.body)
        assert body["error"] == "revoked"

    @pytest.mark.asyncio
    async def test_neither_says_unknown(self, read):
        import json

        for share in (
            _share(expires_at=datetime.now(UTC) - timedelta(days=1)),
            _share(revoked_at=datetime.now(UTC)),
        ):
            body = json.loads((await read(share)).body)
            assert body["error"] != "unknown_error"
