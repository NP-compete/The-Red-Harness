"""E32. The agent can reach a team's artifacts (E31-T1 made it possible)."""

from __future__ import annotations

import pytest

import agent.src.knowledge.artifact_tools as artifact_tools
from agent.src.knowledge.artifact_tools import build_artifact_tools
from agent.src.knowledge.artifacts import ArtifactStore, Owner


@pytest.fixture(autouse=True)
def _restore(monkeypatch):
    """Patched through the fixture, so the next test in this process"""
    yield monkeypatch


def _tools(store, who="ada", teams=("platform",), *, monkeypatch=None):
    (monkeypatch or pytest.MonkeyPatch()).setattr(
        artifact_tools, "_owner_now", lambda: Owner(subject=who, teams=teams)
    )
    return {t.name: t for t in build_artifact_tools(store=store, enabled=True)}


def _store() -> ArtifactStore:
    store = ArtifactStore(max_bytes_per_owner=10_000, max_bytes_per_value=1_000)
    owner = Owner(subject="ada", teams=("platform",))
    store.put(owner, key="mine", value="my tally")
    store.put(owner, key="leaderboard", value="the team's", team="platform")
    return store


class TestReading:
    def test_a_personal_value_comes_back(self, _restore):
        answer = _tools(_store(), monkeypatch=_restore)["read_artifact"].func(
            key="mine"
        )
        assert "my tally" in answer

    def test_a_team_value_comes_back_too(self, _restore):
        answer = _tools(_store(), monkeypatch=_restore)["read_artifact"].func(
            key="leaderboard"
        )
        assert "the team's" in answer

    def test_a_team_value_says_whose_it_is(self, _restore):
        """A value several people can change is not a private note."""
        answer = _tools(_store(), monkeypatch=_restore)["read_artifact"].func(
            key="leaderboard"
        )
        assert "platform" in answer

    def test_somebody_outside_the_team_cannot_read_it(self, _restore):
        answer = _tools(_store(), who="bo", teams=(), monkeypatch=_restore)[
            "read_artifact"
        ].func(key="leaderboard")
        assert "the team's" not in answer
        assert "Nothing is kept under" in answer

    def test_a_missing_key_is_named_rather_than_called_empty(self, _restore):
        answer = _tools(_store(), monkeypatch=_restore)["read_artifact"].func(
            key="nope"
        )
        assert "'nope'" in answer


class TestListing:
    def test_it_lists_both_and_marks_the_shared_one(self, _restore):
        said = _tools(_store(), monkeypatch=_restore)["list_artifacts"].func()
        assert "mine" in said
        assert "leaderboard (shared)" in said

    def test_everything_listed_can_be_read(self, _restore):
        """The failure this guards: a key visible in the list and"""
        tools = _tools(_store(), monkeypatch=_restore)
        for key in ("mine", "leaderboard"):
            assert "Nothing is kept under" not in tools["read_artifact"].func(key=key)

    def test_somebody_outside_the_team_sees_only_their_own(self, _restore):
        store = _store()
        store.put(Owner(subject="bo"), key="bo-only", value="x")
        said = _tools(store, who="bo", teams=(), monkeypatch=_restore)[
            "list_artifacts"
        ].func()
        assert "bo-only" in said
        assert "leaderboard" not in said
