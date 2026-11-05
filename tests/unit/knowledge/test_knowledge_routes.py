"""A person's own documents: add, see, remove."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.scopes import Scope
from agent.src.knowledge.store import Document, InMemoryStore

ON = Knowledge(
    enabled=True,
    scopes=(Scope.SESSION, Scope.USER, Scope.AGENT),
    order=(Scope.SESSION, Scope.USER, Scope.AGENT),
    top_k=8,
    user_max_bytes=1000,
)
OFF = Knowledge()
NO_USER_SCOPE = Knowledge(
    enabled=True, scopes=(Scope.AGENT,), order=(Scope.AGENT,), top_k=8
)


@pytest.fixture
def client() -> TestClient:
    from agent.aegra.http_app import app

    return TestClient(app)


def _store() -> InMemoryStore:
    store = InMemoryStore()
    store.add(Document(id="mine", text="my notes", scope=Scope.USER, owner="alice"))
    store.add(Document(id="theirs", text="their notes", scope=Scope.USER, owner="bob"))
    store.add(Document(id="corpus:a.md", text="the policy", scope=Scope.AGENT))
    return store


def _as(client, method, path, *, store, config=ON, caller="alice", **kwargs):
    with (
        patch(
            "agent.src.agent.config.loader.AgentConfig.get_knowledge_config",
            return_value=config,
        ),
        patch("agent.aegra.knowledge_routes._store", return_value=store),
        patch("agent.aegra.knowledge_routes._owner", return_value=caller),
    ):
        return getattr(client, method)(path, **kwargs)


class TestSeeingWhatIsThere:
    def test_a_person_sees_their_own(self, client):
        found = _as(client, "get", "/knowledge/documents", store=_store()).json()
        assert [d["id"] for d in found["documents"]] == ["mine"]

    def test_they_do_not_see_anybody_elses(self, client):
        found = _as(client, "get", "/knowledge/documents", store=_store()).json()
        assert "theirs" not in {d["id"] for d in found["documents"]}

    def test_they_do_not_see_the_curated_corpus_here(self, client):
        found = _as(client, "get", "/knowledge/documents", store=_store()).json()
        assert "corpus:a.md" not in {d["id"] for d in found["documents"]}

    def test_the_other_person_sees_only_theirs(self, client):
        found = _as(
            client, "get", "/knowledge/documents", store=_store(), caller="bob"
        ).json()
        assert [d["id"] for d in found["documents"]] == ["theirs"]

    def test_it_reports_what_they_have_used(self, client):
        found = _as(client, "get", "/knowledge/documents", store=_store()).json()
        assert found["used_bytes"] == len("my notes")

    def test_it_reports_the_limit(self, client):
        found = _as(client, "get", "/knowledge/documents", store=_store()).json()
        assert found["limit_bytes"] == 1000


class TestAddingOne:
    def test_it_is_stored(self, client):
        store = _store()
        _as(
            client,
            "post",
            "/knowledge/documents",
            store=store,
            json={"title": "Notes", "text": "something new"},
        )
        assert len(store.documents_in(scope=Scope.USER, owner="alice")) == 2

    def test_it_belongs_to_whoever_added_it(self, client):
        store = _store()
        _as(
            client,
            "post",
            "/knowledge/documents",
            store=store,
            json={"title": "Notes", "text": "something new"},
            caller="bob",
        )
        owners = {d.owner for d in store.documents_in(scope=Scope.USER)}
        assert "bob" in owners

    def test_the_identifier_comes_back_so_it_can_be_removed(self, client):
        found = _as(
            client,
            "post",
            "/knowledge/documents",
            store=_store(),
            json={"title": "Notes", "text": "something new"},
        ).json()
        assert found["id"]

    def test_an_empty_document_is_refused(self, client):
        found = _as(
            client,
            "post",
            "/knowledge/documents",
            store=_store(),
            json={"title": "Notes", "text": "   "},
        )
        assert found.status_code == 400

    def test_one_that_would_not_fit_is_refused(self, client):
        found = _as(
            client,
            "post",
            "/knowledge/documents",
            store=_store(),
            json={"title": "Big", "text": "x" * 2000},
        )
        assert found.status_code == 413

    def test_the_refusal_says_how_much_room_there_is(self, client):
        found = _as(
            client,
            "post",
            "/knowledge/documents",
            store=_store(),
            json={"title": "Big", "text": "x" * 2000},
        )
        assert "1000" in found.json()["detail"]

    def test_nothing_is_stored_when_it_is_refused(self, client):
        store = _store()
        _as(
            client,
            "post",
            "/knowledge/documents",
            store=store,
            json={"title": "Big", "text": "x" * 2000},
        )
        assert len(store.documents_in(scope=Scope.USER, owner="alice")) == 1


class TestRemovingOne:
    def test_a_person_can_remove_their_own(self, client):
        store = _store()
        _as(client, "delete", "/knowledge/documents/mine", store=store)
        assert store.documents_in(scope=Scope.USER, owner="alice") == []

    def test_they_cannot_remove_anybody_elses(self, client):
        found = _as(client, "delete", "/knowledge/documents/theirs", store=_store())
        assert found.status_code == 403

    def test_and_it_is_still_there(self, client):
        store = _store()
        _as(client, "delete", "/knowledge/documents/theirs", store=store)
        assert store.documents_in(scope=Scope.USER, owner="bob")

    def test_they_cannot_remove_the_curated_corpus(self, client):
        found = _as(
            client, "delete", "/knowledge/documents/corpus:a.md", store=_store()
        )
        assert found.status_code == 403

    def test_removing_something_that_is_not_there_says_so(self, client):
        found = _as(client, "delete", "/knowledge/documents/nothing", store=_store())
        assert found.status_code == 404


class TestWhenThisIsNotOffered:
    def test_a_library_that_is_off_has_no_page_behind_it(self, client):
        found = _as(client, "get", "/knowledge/documents", store=_store(), config=OFF)
        assert found.status_code == 404

    def test_nor_does_one_that_keeps_no_personal_documents(self, client):
        found = _as(
            client, "get", "/knowledge/documents", store=_store(), config=NO_USER_SCOPE
        )
        assert found.status_code == 404

    def test_and_nothing_can_be_added_to_it(self, client):
        found = _as(
            client,
            "post",
            "/knowledge/documents",
            store=_store(),
            config=NO_USER_SCOPE,
            json={"title": "Notes", "text": "something"},
        )
        assert found.status_code == 404


class TestWhatTheirTeamsShare:
    """Visible, and not theirs to remove."""

    @staticmethod
    def _store_with_teams() -> InMemoryStore:
        store = InMemoryStore()
        store.add(Document(id="mine", text="my notes", scope=Scope.USER, owner="alice"))
        store.add(
            Document(
                id="corpus:teams/platform/runbook.md",
                title="runbook",
                text="restart the ingester",
                scope=Scope.TEAM,
                team="platform",
            )
        )
        store.add(
            Document(
                id="corpus:teams/finance/ledger.md",
                title="ledger",
                text="month end close",
                scope=Scope.TEAM,
                team="finance",
            )
        )
        return store

    @staticmethod
    def _as_member(client, store, teams=("platform",)):
        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_knowledge_config",
                return_value=ON,
            ),
            patch("agent.aegra.knowledge_routes._store", return_value=store),
            patch("agent.aegra.knowledge_routes._owner", return_value="alice"),
            patch("agent.aegra.knowledge_routes._teams_of", return_value=teams),
        ):
            return client.get("/knowledge/documents").json()

    def test_a_members_team_documents_are_listed(self, client):
        found = self._as_member(client, self._store_with_teams())
        assert [d["id"] for d in found["team"]] == ["corpus:teams/platform/runbook.md"]

    def test_another_teams_are_not(self, client):
        found = self._as_member(client, self._store_with_teams())
        assert "corpus:teams/finance/ledger.md" not in {d["id"] for d in found["team"]}

    def test_somebody_in_no_team_sees_none(self, client):
        found = self._as_member(client, self._store_with_teams(), teams=())
        assert found["team"] == []

    def test_each_says_which_team_it_came_from(self, client):
        found = self._as_member(client, self._store_with_teams())
        assert found["team"][0]["team"] == "platform"

    def test_they_are_kept_apart_from_the_personal_ones(self, client):
        found = self._as_member(client, self._store_with_teams())
        assert [d["id"] for d in found["documents"]] == ["mine"]

    def test_they_do_not_count_against_a_personal_quota(self, client):
        found = self._as_member(client, self._store_with_teams())
        assert found["used_bytes"] == len("my notes")

    def test_a_member_cannot_remove_one(self, client):
        store = self._store_with_teams()
        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_knowledge_config",
                return_value=ON,
            ),
            patch("agent.aegra.knowledge_routes._store", return_value=store),
            patch("agent.aegra.knowledge_routes._owner", return_value="alice"),
            patch(
                "agent.aegra.knowledge_routes._teams_of",
                return_value=("platform",),
            ),
        ):
            found = client.delete(
                "/knowledge/documents/corpus:teams/platform/runbook.md"
            )
        assert found.status_code == 403
