"""Who can see which collection, decided before the search runs."""

from __future__ import annotations

import pytest

from agent.src.knowledge.scopes import (
    Collection,
    Scope,
    Viewer,
    can_read,
    retrieval_filter,
)

VIEWER = Viewer(subject="someone@example.com", teams=("sre",), thread_id="t1")


def collection(scope: Scope, **kwargs) -> Collection:
    defaults = {"owner": None, "team": None, "thread_id": None}
    defaults.update(kwargs)
    return Collection(name="c", scope=scope, **defaults)


def test_an_agent_collection_is_visible_to_anyone_using_the_agent():
    assert can_read(collection(Scope.AGENT), VIEWER) is True


def test_a_user_collection_is_visible_to_its_owner():
    assert can_read(collection(Scope.USER, owner="someone@example.com"), VIEWER) is True


def test_a_user_collection_is_invisible_to_everybody_else():
    assert can_read(collection(Scope.USER, owner="other@example.com"), VIEWER) is False


def test_a_team_collection_is_visible_to_a_member():
    assert can_read(collection(Scope.TEAM, team="sre"), VIEWER) is True


def test_a_team_collection_is_invisible_to_a_non_member():
    assert can_read(collection(Scope.TEAM, team="finance"), VIEWER) is False


def test_a_viewer_in_no_team_sees_no_team_collections():
    loner = Viewer(subject="a@example.com", teams=(), thread_id="t1")
    assert can_read(collection(Scope.TEAM, team="sre"), loner) is False


def test_a_session_collection_belongs_to_its_own_conversation():
    assert can_read(collection(Scope.SESSION, thread_id="t1"), VIEWER) is True


def test_a_session_collection_is_invisible_from_another_conversation():
    assert can_read(collection(Scope.SESSION, thread_id="t2"), VIEWER) is False


def test_a_collection_with_no_owner_is_not_readable_as_a_user_collection():
    assert can_read(collection(Scope.USER), VIEWER) is False


def test_the_filter_names_every_scope_the_viewer_may_search():
    assert set(retrieval_filter(VIEWER)["scopes"]) == {
        Scope.AGENT,
        Scope.USER,
        Scope.TEAM,
        Scope.SESSION,
    }


def test_the_filter_pins_the_viewer_identity_so_the_query_does_the_work():
    criteria = retrieval_filter(VIEWER)
    assert criteria["owner"] == "someone@example.com"
    assert criteria["teams"] == ("sre",)
    assert criteria["thread_id"] == "t1"


def test_a_viewer_with_no_thread_cannot_reach_session_collections():
    detached = Viewer(subject="a@example.com", teams=(), thread_id=None)
    assert Scope.SESSION not in retrieval_filter(detached)["scopes"]


@pytest.mark.parametrize("scope", list(Scope))
def test_every_scope_has_a_rule(scope):
    assert isinstance(can_read(collection(scope), VIEWER), bool)
