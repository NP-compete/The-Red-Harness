"""E31-T1. A team corpus is readable by the team and nobody else."""

from __future__ import annotations

import pytest

from agent.src.knowledge import membership
from agent.src.knowledge.config import KnowledgeMisconfigured, read_knowledge
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore


def _store() -> InMemoryStore:
    store = InMemoryStore()
    store.add(
        Document(
            id="d1",
            text="drain the queue with the replay job",
            scope=Scope.TEAM,
            team="platform",
            title="runbook",
        )
    )
    return store


class TestTwoReaders:
    def test_a_member_finds_the_team_corpus(self):
        found = _store().search(
            "replay job",
            scope=Scope.TEAM,
            viewer=Viewer(subject="ada", teams=("platform",), thread_id=None),
        )
        assert [hit.id for hit in found] == ["d1"]

    def test_somebody_in_another_team_finds_nothing(self):
        found = _store().search(
            "replay job",
            scope=Scope.TEAM,
            viewer=Viewer(subject="bo", teams=("finance",), thread_id=None),
        )
        assert list(found) == []

    def test_the_reader_the_product_used_to_build_finds_nothing(self):
        """`teams=()` — the shape every route constructed."""
        found = _store().search(
            "replay job",
            scope=Scope.TEAM,
            viewer=Viewer(subject="ada", teams=(), thread_id=None),
        )
        assert list(found) == []


class TestWhoDecides:
    def test_membership_is_asked_not_stored(self):
        """No member list anywhere in the module."""
        import inspect

        source = inspect.getsource(membership)
        assert "resolve_user_groups" in source
        assert "_is_user_in_group_sync" in source

    @pytest.mark.asyncio
    async def test_an_unreachable_directory_means_no_teams(self, monkeypatch):
        """Less than they should see, never somebody else's."""
        monkeypatch.setattr(membership, "candidate_teams", lambda: ("platform",))
        monkeypatch.setattr("agent.aegra.auth.ENABLE_AUTH", True)

        async def _boom(*_args, **_kwargs):
            raise RuntimeError("ldap is down")

        monkeypatch.setattr("agent.src.ldap.service.resolve_user_groups", _boom)
        assert await membership.teams_of("ada") == ()

    @pytest.mark.asyncio
    async def test_no_configured_teams_asks_nothing(self, monkeypatch):
        monkeypatch.setattr(membership, "candidate_teams", lambda: ())
        assert await membership.teams_of("ada") == ()


class TestCandidates:
    def test_a_corpus_nobody_configured_is_still_reachable(self, monkeypatch):
        """Otherwise ingesting a team folder makes documents nobody"""
        monkeypatch.setattr(membership, "configured_teams", lambda: ("sre",))
        monkeypatch.setattr(membership, "_teams_with_documents", lambda: ("platform",))
        assert membership.candidate_teams() == ("sre", "platform")

    def test_a_team_named_twice_is_asked_about_once(self, monkeypatch):
        monkeypatch.setattr(membership, "configured_teams", lambda: ("platform",))
        monkeypatch.setattr(membership, "_teams_with_documents", lambda: ("platform",))
        assert membership.candidate_teams() == ("platform",)


class TestConfiguration:
    def test_teams_are_read_from_the_agent_file(self):
        found = read_knowledge({"knowledge": {"enabled": True, "teams": ["platform"]}})
        assert found.teams == ("platform",)

    def test_a_bare_string_is_refused(self):
        """`teams: platform,sre` read as one group named"""
        with pytest.raises(KnowledgeMisconfigured, match="list of directory groups"):
            read_knowledge({"knowledge": {"enabled": True, "teams": "platform,sre"}})

    def test_the_same_group_twice_is_refused(self):
        with pytest.raises(KnowledgeMisconfigured, match="same group twice"):
            read_knowledge(
                {"knowledge": {"enabled": True, "teams": ["platform", "platform"]}}
            )

    def test_no_teams_is_no_teams_rather_than_every_team(self):
        assert read_knowledge({"knowledge": {"enabled": True}}).teams == ()
