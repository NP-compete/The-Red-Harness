"""Carrying out a departure, not just describing one."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agent.src.knowledge.scopes import Collection, Scope
from agent.src.security.departure import carry_out, plan_departure

COLLECTIONS = [
    Collection(name="amar-notes", scope=Scope.USER, owner="amar"),
    Collection(name="sre-runbooks", scope=Scope.TEAM, team="sre"),
    Collection(name="handbook", scope=Scope.AGENT),
]


def _plan(subject="amar"):
    return plan_departure(
        subject=subject,
        collections=COLLECTIONS,
        connected_servers=["gitlab", "jira"],
        granted_delegations=["nightly-report"],
    )


class _Doer:
    """Stands in for the things that actually change."""

    def __init__(self, fails_on: str = ""):
        self.revoked: list[str] = []
        self.stopped: list[tuple[str, str]] = []
        self.dropped: list[str] = []
        self._fails_on = fails_on

    async def revoke_connection(self, subject: str, server: str) -> None:
        if self._fails_on == "revoke":
            raise ConnectionError("token store down")
        self.revoked.append(server)

    async def stop_agent(self, name: str, reason: str) -> None:
        if self._fails_on == "stop":
            raise ConnectionError("worker unreachable")
        self.stopped.append((name, reason))

    async def drop_collection(self, name: str) -> None:
        self.dropped.append(name)


class TestWhatGoes:
    @pytest.mark.asyncio
    async def test_every_connection_is_revoked(self):
        doer = _Doer()
        await carry_out(_plan(), doer=doer)
        assert sorted(doer.revoked) == ["gitlab", "jira"]

    @pytest.mark.asyncio
    async def test_unattended_work_is_stopped(self):
        doer = _Doer()
        await carry_out(_plan(), doer=doer)
        assert [name for name, _ in doer.stopped] == ["nightly-report"]

    @pytest.mark.asyncio
    async def test_it_is_stopped_with_a_reason_somebody_can_read(self):
        doer = _Doer()
        await carry_out(_plan(), doer=doer)
        assert "amar" in doer.stopped[0][1]


class TestWhatStays:
    @pytest.mark.asyncio
    async def test_what_they_put_in_a_team_stays(self):
        doer = _Doer()
        await carry_out(_plan(), doer=doer)
        assert "sre-runbooks" not in doer.dropped

    @pytest.mark.asyncio
    async def test_the_shared_corpus_stays(self):
        doer = _Doer()
        await carry_out(_plan(), doer=doer)
        assert "handbook" not in doer.dropped

    @pytest.mark.asyncio
    async def test_their_own_collections_go(self):
        doer = _Doer()
        await carry_out(_plan(), doer=doer)
        assert doer.dropped == ["amar-notes"]


class TestWhenSomethingFails:
    @pytest.mark.asyncio
    async def test_a_failed_revocation_does_not_abandon_the_rest(self):
        doer = _Doer(fails_on="revoke")
        await carry_out(_plan(), doer=doer)
        assert doer.stopped and doer.dropped

    @pytest.mark.asyncio
    async def test_and_it_is_reported_rather_than_swallowed(self):
        doer = _Doer(fails_on="revoke")
        found = await carry_out(_plan(), doer=doer)
        assert found.failed

    @pytest.mark.asyncio
    async def test_the_report_names_what_did_not_happen(self):
        doer = _Doer(fails_on="revoke")
        found = await carry_out(_plan(), doer=doer)
        assert any("gitlab" in said for said in found.failed)

    @pytest.mark.asyncio
    async def test_a_clean_departure_reports_nothing_outstanding(self):
        found = await carry_out(_plan(), doer=_Doer())
        assert found.failed == []

    @pytest.mark.asyncio
    async def test_it_says_what_it_did(self):
        found = await carry_out(_plan(), doer=_Doer())
        assert found.done


class TestTheRealDoer:
    @pytest.mark.asyncio
    async def test_revoking_reaches_the_token_store(self):
        from agent.src.security.departure import LiveDeparture

        store = AsyncMock()
        with patch("agent.aegra.mcp_token_store.McpTokenStore", return_value=store):
            await LiveDeparture().revoke_connection("amar", "gitlab")
        assert store.delete_token.await_count == 1


class TestItIsWrittenDown:
    @staticmethod
    def _doc():
        from pathlib import Path

        return (
            Path(__file__).resolve().parents[3]
            / "docs"
            / "security"
            / "authorization.md"
        )

    def test_the_departure_rules_are_recorded(self):
        assert "When somebody leaves" in self._doc().read_text()

    def test_it_says_team_content_is_kept(self):
        said = self._doc().read_text().lower()
        assert "kept" in said and "never theirs alone" in said
