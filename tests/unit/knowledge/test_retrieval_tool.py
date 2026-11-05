"""The library, as something the model can call."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.scopes import Scope
from agent.src.knowledge.store import Document, InMemoryStore
from agent.src.knowledge.tools import build_retrieval_tool

ON = Knowledge(
    enabled=True,
    scopes=(Scope.SESSION, Scope.USER, Scope.AGENT),
    order=(Scope.SESSION, Scope.USER, Scope.AGENT),
    top_k=8,
)


def _store() -> InMemoryStore:
    store = InMemoryStore()
    store.add(
        Document(
            id="corpus:leave.md",
            title="leave",
            text="Staff accrue 25 days of annual leave",
            scope=Scope.AGENT,
        )
    )
    store.add(
        Document(
            id="u1",
            title="mine",
            text="my own leave notes",
            scope=Scope.USER,
            owner="alice",
        )
    )
    store.add(
        Document(
            id="s1",
            title="attached",
            text="leave request form",
            scope=Scope.SESSION,
            thread_id="t1",
        )
    )
    return store


def _call(arguments: dict, *, config=ON, store=None, who="alice", thread="t1"):
    tool = build_retrieval_tool(config=config, store=store or _store())
    with (
        patch("agent.src.knowledge.tools.resolve_user_id", return_value=who),
        patch("agent.src.knowledge.tools.resolve_thread_id", return_value=thread),
    ):
        return tool.invoke(arguments)


class TestWhetherThereIsATool:
    def test_a_library_that_is_off_offers_none(self):
        assert build_retrieval_tool(config=Knowledge(), store=_store()) is None

    def test_a_library_that_is_on_offers_one(self):
        assert build_retrieval_tool(config=ON, store=_store()) is not None

    def test_it_has_a_name_the_model_can_call(self):
        assert build_retrieval_tool(config=ON, store=_store()).name

    def test_its_description_says_what_it_searches(self):
        said = build_retrieval_tool(config=ON, store=_store()).description.lower()
        assert "document" in said


class TestAskingIt:
    def test_it_finds_something(self):
        assert "leave" in _call({"question": "leave"})

    def test_it_names_the_document(self):
        assert "corpus:leave.md" in _call({"question": "annual"}, store=_agent_only())

    def test_it_says_which_scope_answered(self):
        assert "agent" in _call({"question": "annual"}, store=_agent_only()).lower()

    def test_finding_nothing_says_so_plainly(self):
        found = _call({"question": "zebra"})
        assert "nothing" in found.lower() or "no " in found.lower()

    def test_finding_nothing_is_not_an_error(self):
        assert isinstance(_call({"question": "zebra"}), str)


class TestWhoIsAsking:
    def test_it_searches_as_the_person_who_asked(self):
        found = _call({"question": "my own", "scope": "user"}, who="alice")
        assert "u1" in found

    def test_another_person_does_not_see_those_documents(self):
        found = _call({"question": "my own", "scope": "user"}, who="bob")
        assert "u1" not in found

    def test_it_searches_the_conversation_it_was_called_in(self):
        found = _call({"question": "request", "scope": "session"}, thread="t1")
        assert "s1" in found

    def test_another_conversation_does_not_see_those(self):
        found = _call({"question": "request", "scope": "session"}, thread="t2")
        assert "s1" not in found

    def test_a_call_with_no_identity_still_reaches_the_curated_corpus(self):
        found = _call({"question": "annual", "scope": "agent"}, who=None)
        assert "corpus:leave.md" in found


class TestRefusingInAFormTheModelCanUse:
    def test_a_scope_that_is_off_comes_back_as_text(self):
        narrow = Knowledge(
            enabled=True, scopes=(Scope.AGENT,), order=(Scope.AGENT,), top_k=8
        )
        found = _call({"question": "leave", "scope": "user"}, config=narrow)
        assert isinstance(found, str)

    def test_and_says_which_scope(self):
        narrow = Knowledge(
            enabled=True, scopes=(Scope.AGENT,), order=(Scope.AGENT,), top_k=8
        )
        assert "user" in _call({"question": "leave", "scope": "user"}, config=narrow)

    def test_a_scope_that_does_not_exist_comes_back_as_text(self):
        found = _call({"question": "leave", "scope": "everything"})
        assert isinstance(found, str) and "everything" in found

    def test_an_empty_question_comes_back_as_text(self):
        assert isinstance(_call({"question": "   "}), str)

    def test_a_store_that_is_down_does_not_end_the_turn(self):
        class _Broken:
            def search(self, *args, **kwargs):
                raise ConnectionError("store unavailable")

        found = _call({"question": "leave"}, store=_Broken())
        assert isinstance(found, str)

    def test_and_the_message_says_the_lookup_failed(self):
        class _Broken:
            def search(self, *args, **kwargs):
                raise ConnectionError("store unavailable")

        assert "could not" in _call({"question": "leave"}, store=_Broken()).lower()


class TestTheGraphOffersIt:
    def test_the_builder_is_reached_from_the_graph(self):
        import inspect

        from agent.aegra import graph

        assert "build_retrieval_tool" in inspect.getsource(graph)

    def test_it_is_offered_before_the_capability_check(self):
        import inspect

        from agent.aegra import graph

        source = inspect.getsource(graph)
        assert source.index("build_retrieval_tool") < source.index(
            "resolve_capability_manifest("
        )


def _agent_only() -> InMemoryStore:
    store = InMemoryStore()
    store.add(
        Document(
            id="corpus:leave.md",
            title="leave",
            text="Staff accrue 25 days of annual leave",
            scope=Scope.AGENT,
        )
    )
    return store


@pytest.mark.parametrize("scope", ["session", "user", "agent"])
def test_every_kept_scope_can_be_named(scope):
    assert isinstance(_call({"question": "leave", "scope": scope}), str)


class TestWhatTravelsBesideTheText:
    """The model reads prose; the citation layer needs structure."""

    def test_the_documents_travel_as_data(self):
        tool = build_retrieval_tool(config=ON, store=_agent_only())
        with (
            patch("agent.src.knowledge.tools.resolve_user_id", return_value="alice"),
            patch("agent.src.knowledge.tools.resolve_thread_id", return_value="t1"),
        ):
            text, artifact = tool.func("annual", "agent")
        assert isinstance(text, str) and isinstance(artifact, list)

    def test_each_carries_what_a_citation_needs(self):
        tool = build_retrieval_tool(config=ON, store=_agent_only())
        with (
            patch("agent.src.knowledge.tools.resolve_user_id", return_value="alice"),
            patch("agent.src.knowledge.tools.resolve_thread_id", return_value="t1"),
        ):
            _text, artifact = tool.func("annual", "agent")
        assert set(artifact[0]) >= {"id", "title", "text", "scope"}

    def test_a_refusal_carries_no_documents(self):
        tool = build_retrieval_tool(config=ON, store=_agent_only())
        with (
            patch("agent.src.knowledge.tools.resolve_user_id", return_value="alice"),
            patch("agent.src.knowledge.tools.resolve_thread_id", return_value="t1"),
        ):
            _text, artifact = tool.func("   ", "")
        assert artifact == []

    def test_the_tool_is_declared_as_carrying_both(self):
        tool = build_retrieval_tool(config=ON, store=_agent_only())
        assert tool.response_format == "content_and_artifact"
