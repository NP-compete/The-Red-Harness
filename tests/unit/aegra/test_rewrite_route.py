"""The door the note editor knocks on to have a passage rewritten."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.aegra import knowledge_routes


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(knowledge_routes.router)
    return TestClient(app)


def _as(user: str = "ada"):
    return patch.object(knowledge_routes, "_owner", new=_returning(user))


def _returning(value):
    async def answer(_request):
        return value

    return answer


class TestAnOrdinaryRewrite:
    def test_the_rewritten_passage_comes_back(self, client):
        with (
            _as(),
            patch.object(knowledge_routes, "_ask_model", return_value="tightened"),
        ):
            answer = client.post(
                "/knowledge/rewrite",
                json={"selection": "a long rambling passage", "instruction": "shorter"},
            )
        assert answer.status_code == 200
        assert answer.json()["text"] == "tightened"

    def test_the_selection_reaches_the_model_inside_the_fence(self, client):
        from agent.src.security.fencing import FENCE

        with (
            _as(),
            patch.object(
                knowledge_routes, "_ask_model", return_value="tightened"
            ) as asked,
        ):
            client.post(
                "/knowledge/rewrite",
                json={"selection": "a passage", "instruction": "shorter"},
            )
        prompt = asked.call_args[0][0]
        assert prompt.count(FENCE) == 2
        assert "a passage" in prompt.split(FENCE)[1]


class TestWhenTheRewriteCannotBeUsed:
    def test_nothing_back_is_a_plain_refusal_not_an_error(self, client):
        with _as(), patch.object(knowledge_routes, "_ask_model", return_value=""):
            answer = client.post(
                "/knowledge/rewrite",
                json={"selection": "a passage", "instruction": "shorter"},
            )
        assert answer.status_code == 200
        body = answer.json()
        assert body["ok"] is False
        assert "unchanged" in body["reason"].lower()
        assert body["text"] == ""

    def test_a_model_that_raises_does_not_become_a_stack_trace(self, client):
        with (
            _as(),
            patch.object(
                knowledge_routes, "_ask_model", side_effect=RuntimeError("unreachable")
            ),
        ):
            answer = client.post(
                "/knowledge/rewrite",
                json={"selection": "a passage", "instruction": "shorter"},
            )
        assert answer.status_code == 200
        assert answer.json()["ok"] is False

    def test_an_empty_selection_never_reaches_the_model(self, client):
        with _as(), patch.object(knowledge_routes, "_ask_model") as asked:
            answer = client.post(
                "/knowledge/rewrite", json={"selection": "  ", "instruction": "shorter"}
            )
        assert answer.json()["ok"] is False
        asked.assert_not_called()


class TestTheModelCallIsReal:
    """Everything above mocks `_ask_model`, so none of it runs it."""

    def test_it_builds_a_model_and_returns_what_the_model_said(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        built = MagicMock()
        built.invoke.return_value = SimpleNamespace(content="tightened")

        with patch(
            "agent.src.cache.model_cache.get_or_create_model",
            return_value=built,
        ) as factory:
            answer = knowledge_routes._ask_model("rewrite this")

        assert answer == "tightened"
        assert built.invoke.call_args[0][0] == "rewrite this"
        assert factory.call_args.kwargs["model_name"]

    def test_a_reply_with_no_content_becomes_an_empty_string(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        built = MagicMock()
        built.invoke.return_value = SimpleNamespace(content=None)

        with patch(
            "agent.src.cache.model_cache.get_or_create_model",
            return_value=built,
        ):
            assert knowledge_routes._ask_model("rewrite this") == ""


class TestTheDoorIsNotOpen:
    def test_a_caller_with_no_identity_is_refused(self, client):
        async def nobody(_request):
            raise knowledge_routes.HTTPException(status_code=401, detail="no identity")

        with (
            patch.object(knowledge_routes, "_owner", new=nobody),
            patch.object(knowledge_routes, "_ask_model") as asked,
        ):
            answer = client.post(
                "/knowledge/rewrite",
                json={"selection": "a passage", "instruction": "shorter"},
            )
        assert answer.status_code == 401
        asked.assert_not_called()
