"""Deciding from inside a running event loop."""

from __future__ import annotations

import pytest

from agent.src.security.authority import CredentialAuthoritySource
from agent.src.security.resolver import (
    Allowed,
    Budget,
    Identity,
    NeedsApproval,
    RefusalCode,
    Refused,
    RunContext,
    ToolCall,
    resolve_async,
)

CTX = RunContext(identity=Identity(subject="someone@example.com"))
CALL = ToolCall(name="tracker.search", server="tracker")
SERVERS = {"tracker": {"url": "https://tracker"}}


class SyncAuthority:
    def holds(self, identity, call):
        return True


class AsyncAuthority:
    def __init__(self, held=True):
        self._held = held

    async def holds(self, identity, call):
        return self._held


class Policy:
    def __init__(self, grade="allow"):
        self._grade = grade

    def decide(self, identity, call):
        return (self._grade, "medium", "")


class NoBudget:
    def remaining(self, ctx, call=None):
        return Budget()


class Connected:
    async def has_valid_token(self, user_id, mcp_name, server_cfg, *, verify=False):
        return True


async def decide(**over):
    sources = {"authority": AsyncAuthority(), "policy": Policy(), "budget": NoBudget()}
    sources.update(over)
    return await resolve_async(CTX, CALL, **sources)


@pytest.mark.asyncio
async def test_an_async_authority_is_awaited():
    assert isinstance(await decide(), Allowed)


@pytest.mark.asyncio
async def test_a_sync_authority_still_works():
    assert isinstance(await decide(authority=SyncAuthority()), Allowed)


@pytest.mark.asyncio
async def test_a_refusal_comes_back_the_same_way():
    decision = await decide(authority=AsyncAuthority(held=False))
    assert isinstance(decision, Refused)
    assert decision.code is RefusalCode.NO_AUTHORITY


@pytest.mark.asyncio
async def test_approval_comes_back_the_same_way():
    assert isinstance(await decide(policy=Policy(grade="ask")), NeedsApproval)


@pytest.mark.asyncio
async def test_the_credential_source_works_inside_a_loop():
    source = CredentialAuthoritySource(Connected(), SERVERS)
    assert await source.aholds(CTX.identity, CALL) is True


def test_the_sync_path_is_unchanged_outside_a_loop():
    source = CredentialAuthoritySource(Connected(), SERVERS)
    assert source.holds(CTX.identity, CALL) is True
