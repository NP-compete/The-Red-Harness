"""Deciding whether the asking identity holds the credential a tool needs."""

from __future__ import annotations

import pytest

from agent.src.security.authority import CredentialAuthoritySource
from agent.src.security.resolver import Identity, ToolCall

SOMEONE = Identity(subject="someone@example.com")
SERVERS = {"tracker": {"url": "https://tracker.example"}}


class StubResolver:
    def __init__(self, answer: bool | Exception = True) -> None:
        self._answer = answer
        self.seen: list[tuple[str, str, bool]] = []

    async def has_valid_token(self, user_id, mcp_name, server_cfg, *, verify=False):
        self.seen.append((user_id, mcp_name, verify))
        if isinstance(self._answer, Exception):
            raise self._answer
        return self._answer


def source(answer: bool | Exception = True, servers=None) -> CredentialAuthoritySource:
    return CredentialAuthoritySource(
        credentials=StubResolver(answer),
        servers=SERVERS if servers is None else servers,
    )


def test_a_local_tool_needs_no_credential():
    assert source().holds(SOMEONE, ToolCall(name="write_file")) is True


def test_a_connected_server_is_held():
    assert (
        source(True).holds(SOMEONE, ToolCall(name="search", server="tracker")) is True
    )


def test_an_unconnected_server_is_not_held():
    assert (
        source(False).holds(SOMEONE, ToolCall(name="search", server="tracker")) is False
    )


def test_an_unknown_server_is_not_held():
    assert source(True).holds(SOMEONE, ToolCall(name="search", server="nope")) is False


def test_an_unreachable_credential_store_is_unknown():
    assert (
        source(RuntimeError("boom")).holds(
            SOMEONE, ToolCall(name="s", server="tracker")
        )
        is None
    )


def test_it_asks_about_the_identity_that_is_calling():
    stub = StubResolver(True)
    CredentialAuthoritySource(credentials=stub, servers=SERVERS).holds(
        Identity(subject="other@example.com"), ToolCall(name="search", server="tracker")
    )
    assert stub.seen[0][0] == "other@example.com"


def test_it_verifies_rather_than_trusting_a_stored_refresh_token():
    stub = StubResolver(True)
    CredentialAuthoritySource(credentials=stub, servers=SERVERS).holds(
        SOMEONE, ToolCall(name="search", server="tracker")
    )
    assert stub.seen[0][2] is True


def test_a_delegated_run_uses_the_granter_credential():
    stub = StubResolver(True)
    CredentialAuthoritySource(credentials=stub, servers=SERVERS).holds(
        Identity(subject="scheduler", delegated_by="someone@example.com"),
        ToolCall(name="search", server="tracker"),
    )
    assert stub.seen[0][0] == "someone@example.com"


@pytest.mark.parametrize("server", ["", None])
def test_a_blank_server_is_treated_as_local(server):
    assert source().holds(SOMEONE, ToolCall(name="ls", server=server)) is True
