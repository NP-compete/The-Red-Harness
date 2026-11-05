"""A team's documents, visible to its members and nobody else."""

from __future__ import annotations

import pytest

from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore, ScopeViolation

AMAR = Viewer(subject="amar", teams=("platform",), thread_id="t1")
BEA = Viewer(subject="bea", teams=("platform",), thread_id="t2")
CHEN = Viewer(subject="chen", teams=("finance",), thread_id="t3")
LONER = Viewer(subject="dee", teams=(), thread_id="t4")


def _store() -> InMemoryStore:
    store = InMemoryStore()
    store.add(
        Document(
            id="team:runbook",
            text="the deploy runbook",
            scope=Scope.TEAM,
            team="platform",
        )
    )
    store.add(
        Document(
            id="team:ledger",
            text="the deploy ledger",
            scope=Scope.TEAM,
            team="finance",
        )
    )
    store.add(
        Document(id="amar-own", text="the deploy notes", scope=Scope.USER, owner="amar")
    )
    return store


class TestAMemberCanSeeIt:
    def test_the_person_who_added_it(self):
        found = _store().search("deploy", scope=Scope.TEAM, viewer=AMAR)
        assert [d.id for d in found] == ["team:runbook"]

    def test_and_their_colleague(self):
        found = _store().search("deploy", scope=Scope.TEAM, viewer=BEA)
        assert [d.id for d in found] == ["team:runbook"]

    def test_by_identifier_too(self):
        assert _store().get("team:runbook", viewer=BEA) is not None


class TestSomebodyElseCannot:
    def test_a_member_of_a_different_team(self):
        found = _store().search("deploy", scope=Scope.TEAM, viewer=CHEN)
        assert "team:runbook" not in {d.id for d in found}

    def test_they_see_their_own_team_instead(self):
        found = _store().search("deploy", scope=Scope.TEAM, viewer=CHEN)
        assert [d.id for d in found] == ["team:ledger"]

    def test_somebody_in_no_team_sees_nothing(self):
        assert _store().search("deploy", scope=Scope.TEAM, viewer=LONER) == []

    def test_reaching_for_it_by_identifier_is_refused(self):
        with pytest.raises(ScopeViolation):
            _store().get("team:runbook", viewer=CHEN)

    def test_and_the_refusal_gives_nothing_away(self):
        try:
            _store().get("team:runbook", viewer=CHEN)
        except ScopeViolation as refused:
            assert "runbook" not in str(refused).replace("team:runbook", "")


class TestItDoesNotBleedIntoTheOtherScopes:
    def test_a_team_search_returns_no_personal_documents(self):
        found = _store().search("deploy", scope=Scope.TEAM, viewer=AMAR)
        assert "amar-own" not in {d.id for d in found}

    def test_a_personal_search_returns_no_team_documents(self):
        found = _store().search("deploy", scope=Scope.USER, viewer=AMAR)
        assert [d.id for d in found] == ["amar-own"]

    def test_a_colleague_still_cannot_read_a_personal_document(self):
        found = _store().search("deploy", scope=Scope.USER, viewer=BEA)
        assert found == []


class TestAnIncoherentTeamDocument:
    def test_one_with_no_team_is_refused(self):
        store = InMemoryStore()
        with pytest.raises(ValueError):
            store.add(Document(id="x", text="t", scope=Scope.TEAM))

    def test_one_with_an_owner_as_well_is_refused(self):
        store = InMemoryStore()
        with pytest.raises(ValueError):
            store.add(
                Document(
                    id="x", text="t", scope=Scope.TEAM, team="platform", owner="amar"
                )
            )


class TestNoMemberListLivesHere:
    def test_the_store_never_asks_who_is_in_a_team(self):
        import inspect

        from agent.src.knowledge import store as module

        source = inspect.getsource(module)
        for forbidden in ("members_of", "team_members", "lookup_team", "TEAMS"):
            assert forbidden not in source

    def test_membership_arrives_on_the_viewer(self):
        assert "teams" in Viewer.__dataclass_fields__


class TestTheDeploymentDecidesWhetherToKeepIt:
    """A team scope on by default would publish one person's"""

    @staticmethod
    def _read(**scopes):
        from agent.src.knowledge.config import read_knowledge

        return read_knowledge({"knowledge": {"enabled": True, "scopes": scopes}})

    def test_it_is_kept_by_default_like_the_others(self):
        assert Scope.TEAM in self._read().scopes

    def test_turning_it_off_removes_it(self):
        found = self._read(team=False)
        assert Scope.TEAM not in found.scopes

    def test_and_removes_it_from_the_walk(self):
        assert Scope.TEAM not in self._read(team=False).order

    def test_it_sits_between_a_person_and_the_whole_agent(self):
        order = self._read().order
        assert (
            order.index(Scope.USER) < order.index(Scope.TEAM) < order.index(Scope.AGENT)
        )
