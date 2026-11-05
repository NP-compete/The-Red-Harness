"""Getting "why not" out of retrieval and in front of somebody."""

from __future__ import annotations

from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, Hit, InMemoryStore
from agent.src.knowledge.tools import build_retrieval_tool

ALICE = Viewer(subject="alice", teams=(), thread_id="t1")


def _config(min_score=0.5):
    return Knowledge(
        enabled=True,
        scopes=(Scope.USER,),
        order=(Scope.USER,),
        top_k=8,
        min_score=min_score,
    )


def _store():
    store = InMemoryStore()
    store.add(
        Document(
            id="strong",
            text="the daily spend limit refuses a run",
            scope=Scope.USER,
            owner="alice",
            title="Strong",
        )
    )
    store.add(
        Document(
            id="weak",
            text="a limit on something else entirely",
            scope=Scope.USER,
            owner="alice",
            title="Weak",
        )
    )
    return store


def _searched(question="daily spend limit", min_score=0.5):
    from unittest.mock import patch

    tool = build_retrieval_tool(config=_config(min_score), store=_store())
    with (
        patch("agent.src.knowledge.tools.resolve_user_id", return_value="alice"),
        patch("agent.src.knowledge.tools.resolve_thread_id", return_value="t1"),
    ):
        return tool.func(question)


class TestWhatTheModelIsTold:
    def test_it_still_gets_what_was_found(self):
        said, _artifact = _searched()
        assert "Strong" in said

    def test_it_is_told_something_nearly_matched(self):
        said, _artifact = _searched()
        assert "nearly" in said.lower()

    def test_it_is_told_how_many(self):
        said, _artifact = _searched()
        assert "1" in said

    def test_it_is_not_shown_the_text(self):
        said, _artifact = _searched()
        assert "something else entirely" not in said

    def test_nothing_near_means_nothing_said_about_it(self):
        said, _artifact = _searched(min_score=0.0)
        assert "nearly" not in said.lower()

    def test_a_question_that_found_nothing_still_says_what_was_near(self):
        said, _artifact = _searched(question="limit nowhere", min_score=0.99)
        assert "nearly" in said.lower()


class TestWhatTravelsForThePerson:
    def test_a_used_document_carries_its_score(self):
        _said, artifact = _searched()
        used = next(entry for entry in artifact if entry["id"] == "strong")
        assert used["score"] > 0

    def test_a_used_document_says_it_was_used(self):
        _said, artifact = _searched()
        used = next(entry for entry in artifact if entry["id"] == "strong")
        assert used["used"] is True

    def test_a_near_miss_travels_too(self):
        _said, artifact = _searched()
        assert any(entry["id"] == "weak" for entry in artifact)

    def test_a_near_miss_says_it_was_not_used(self):
        _said, artifact = _searched()
        missed = next(entry for entry in artifact if entry["id"] == "weak")
        assert missed["used"] is False

    def test_a_near_miss_carries_its_score(self):
        _said, artifact = _searched()
        missed = next(entry for entry in artifact if entry["id"] == "weak")
        assert 0 < missed["score"] < 0.5

    def test_a_near_miss_carries_no_text(self):
        _said, artifact = _searched()
        missed = next(entry for entry in artifact if entry["id"] == "weak")
        assert not missed.get("text")

    def test_a_near_miss_keeps_its_title(self):
        _said, artifact = _searched()
        missed = next(entry for entry in artifact if entry["id"] == "weak")
        assert missed["title"] == "Weak"


class TestTheHitIsUsable:
    def test_a_hit_can_be_built_from_a_document_and_a_score(self):
        found = Hit(document=Document(id="x", text="t", scope=Scope.AGENT), score=0.5)
        assert found.score == 0.5


class TestItReachesTheTurn:
    """A score computed and never written down shows nobody anything."""

    @staticmethod
    def _noted(artifact, answer="The limit is five."):
        from agent.src.knowledge.citation_middleware import stamp_citations

        class _Tool:
            type = "tool"
            name = "search_documents"

            def __init__(self, entries):
                self.artifact = entries

        class _Answer:
            def __init__(self, text):
                self.content = text
                self.additional_kwargs = {}

        message = _Answer(answer)
        stamp_citations(message, [_Tool(artifact)])
        return message.additional_kwargs.get("answer_notes", {})

    @staticmethod
    def _entries():
        return [
            {
                "id": "strong",
                "title": "Strong",
                "text": "The limit is five.",
                "scope": "user",
                "score": 1.0,
                "used": True,
            },
            {
                "id": "weak",
                "title": "Weak",
                "text": "",
                "scope": "user",
                "score": 0.33,
                "used": False,
            },
        ]

    def test_what_was_looked_at_is_recorded(self):
        assert self._noted(self._entries()).get("retrieval")

    def test_a_used_document_is_listed_with_its_score(self):
        found = self._noted(self._entries())["retrieval"]
        used = next(row for row in found if row["id"] == "strong")
        assert used["score"] == 1.0

    def test_a_near_miss_is_listed_too(self):
        found = self._noted(self._entries())["retrieval"]
        assert any(row["id"] == "weak" for row in found)

    def test_a_near_miss_says_it_was_not_used(self):
        found = self._noted(self._entries())["retrieval"]
        missed = next(row for row in found if row["id"] == "weak")
        assert missed["used"] is False

    def test_no_text_travels_with_it(self):
        found = self._noted(self._entries())["retrieval"]
        assert all("text" not in row for row in found)

    def test_the_citations_are_still_written(self):
        assert self._noted(self._entries()).get("citations")

    def test_a_turn_that_searched_nothing_records_nothing(self):
        assert "retrieval" not in self._noted([])

    def test_a_near_miss_alone_is_still_worth_recording(self):
        found = self._noted(
            [self._entries()[1]], answer="I could not find anything about that."
        )
        assert found.get("retrieval")


class TestATurnThatSearchedTwice:
    """One row per document, not one per search."""

    @staticmethod
    def _rows(entries):
        from agent.src.knowledge.citation_middleware import _looked_at

        return _looked_at(entries)

    @staticmethod
    def _entry(score, used=True, id="doc"):
        return {
            "id": id,
            "title": "Doc",
            "text": "",
            "scope": "user",
            "score": score,
            "used": used,
        }

    def test_a_document_found_twice_is_listed_once(self):
        assert len(self._rows([self._entry(1.0), self._entry(0.5)])) == 1

    def test_the_best_score_is_the_one_kept(self):
        assert self._rows([self._entry(0.5), self._entry(1.0)])[0]["score"] == 1.0

    def test_a_document_used_in_either_search_counts_as_used(self):
        found = self._rows([self._entry(0.1, used=False), self._entry(0.9, used=True)])
        assert found[0]["used"] is True

    def test_different_documents_are_still_listed_separately(self):
        found = self._rows([self._entry(1.0, id="a"), self._entry(0.5, id="b")])
        assert len(found) == 2
