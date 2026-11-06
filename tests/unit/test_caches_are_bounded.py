"""Every per-user cache evicts (SCALE-3)."""

from __future__ import annotations

import pytest

from agent.aegra import mcp


@pytest.fixture(autouse=True)
def empty():
    mcp._user_token_cache.clear()
    yield
    mcp._user_token_cache.clear()


class TestItStopsGrowing:
    def test_it_holds_at_the_bound(self):
        for n in range(mcp._MAX_USER_TOKENS + 50):
            mcp._remember_user_token(f"user-{n}", ("access", "refresh"))
        assert len(mcp._user_token_cache) == mcp._MAX_USER_TOKENS

    def test_the_oldest_goes_first(self):
        for n in range(mcp._MAX_USER_TOKENS + 1):
            mcp._remember_user_token(f"user-{n}", ("access", "refresh"))
        assert "user-0" not in mcp._user_token_cache
        assert f"user-{mcp._MAX_USER_TOKENS}" in mcp._user_token_cache

    def test_using_a_user_keeps_them(self):
        """Least *recently used*, not oldest inserted."""
        mcp._remember_user_token("ada", ("access", "refresh"))
        for n in range(mcp._MAX_USER_TOKENS - 1):
            mcp._remember_user_token(f"user-{n}", ("access", "refresh"))
        mcp._remember_user_token("ada", ("newer", "refresh"))
        mcp._remember_user_token("one-too-many", ("access", "refresh"))

        assert "ada" in mcp._user_token_cache
        assert mcp._user_token_cache["ada"] == ("newer", "refresh")


class TestItStillDoesItsJob:
    def test_a_refresh_is_visible_to_another_task(self):
        mcp._remember_user_token("ada", ("access-2", "refresh-2"))
        assert mcp._user_token_cache.get("ada") == ("access-2", "refresh-2")

    def test_the_bound_is_not_so_small_it_thrashes(self):
        assert mcp._MAX_USER_TOKENS >= 128
