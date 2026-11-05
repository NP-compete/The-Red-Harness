"""The id a page writes under must be the id a run reads."""

from __future__ import annotations

import inspect

import pytest

from agent.aegra import knowledge_routes, limits_routes
from agent.aegra.auth_helpers import memory_user_id


class _Request:
    def __init__(self, headers=None):
        self.headers = headers or {}


class TestWhatTheHelperAnswers:
    @pytest.mark.asyncio
    async def test_with_auth_off_it_honours_who_the_caller_said_they_were(self):
        from unittest.mock import patch

        with patch("agent.aegra.auth.ENABLE_AUTH", False):
            found = await memory_user_id(_Request({"x-user-id": "johnwick"}))
        assert found == "johnwick"

    @pytest.mark.asyncio
    async def test_with_auth_off_and_nobody_named_it_falls_back(self):
        from unittest.mock import patch

        with patch("agent.aegra.auth.ENABLE_AUTH", False):
            found = await memory_user_id(_Request())
        assert found


class TestTheDocumentPagesUseIt:
    """Otherwise an upload lands somewhere the agent cannot read."""

    def test_the_owner_comes_from_the_same_helper_runs_use(self):
        assert "memory_user_id" in inspect.getsource(knowledge_routes._owner)

    def test_it_is_not_the_token_subject(self):
        assert "authenticated_user_id" not in inspect.getsource(knowledge_routes._owner)


class TestTheAllowancePageUsesIt:
    """Otherwise it reads a counter the runs never wrote."""

    def test_the_person_comes_from_the_same_helper(self):
        assert "memory_user_id" in inspect.getsource(limits_routes._who)

    def test_it_is_not_the_token_subject(self):
        assert "authenticated_user_id" not in inspect.getsource(limits_routes._who)


class TestTheyAgreeWithWhatARunResolves:
    """The whole point, asserted end to end rather than by eye."""

    @pytest.mark.asyncio
    async def test_a_page_and_a_run_name_the_same_person(self):
        from unittest.mock import patch

        from agent.src.infrastructure.backend import _get_user_id_from_runtime

        class _Runtime:
            config = {"configurable": {"user_id": "johnwick"}}

        with patch("agent.aegra.auth.ENABLE_AUTH", False):
            from_page = await knowledge_routes._owner(
                _Request({"x-user-id": "johnwick"})
            )

        assert from_page == _get_user_id_from_runtime(_Runtime())
