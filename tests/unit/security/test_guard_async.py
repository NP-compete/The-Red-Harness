"""The guard, used from where the agent actually runs."""

from __future__ import annotations

import pytest

from agent.src.agent.config.middleware import (
    ApprovalPolicy,
    HumanApprovalConfig,
    MiddlewareDefaults,
    MiddlewareFileConfig,
    ToolCallLimitConfig,
    ToolOutputConfig,
    resolve_middleware,
)
from agent.src.security.guard import build_guard
from agent.src.security.resolver import (
    Allowed,
    Identity,
    NeedsApproval,
    RefusalCode,
    Refused,
    ToolCall,
)
from agent.src.security.trust import ToolResult

SERVERS = {"tracker": {"url": "https://tracker"}, "docs": {"url": "https://docs"}}
SOMEONE = Identity(subject="someone@example.com")
CREATE = ToolCall(name="tracker.create_issue", server="tracker", writes=True)


class Connected:
    async def has_valid_token(self, user_id, mcp_name, server_cfg, *, verify=False):
        return True


class NotConnected:
    async def has_valid_token(self, user_id, mcp_name, server_cfg, *, verify=False):
        return False


def config(**defaults):
    base = {
        "human_approval": HumanApprovalConfig(default_decision="allow"),
        "tool_output": ToolOutputConfig(trusted_servers=["docs"]),
        "tool_call_limit": ToolCallLimitConfig(run_limit=10),
    }
    base.update(defaults)
    return resolve_middleware(
        MiddlewareFileConfig(defaults=MiddlewareDefaults(**base)), "any-model"
    )


def guard(credentials=None, cfg=None):
    return build_guard(
        config=cfg or config(),
        credentials=credentials or Connected(),
        servers=SERVERS,
        identity=SOMEONE,
    )


@pytest.mark.asyncio
async def test_it_authorises_from_inside_a_loop():
    assert isinstance(await guard().aauthorise(CREATE), Allowed)


@pytest.mark.asyncio
async def test_an_unconnected_system_is_refused():
    decision = await guard(credentials=NotConnected()).aauthorise(CREATE)
    assert isinstance(decision, Refused)
    assert decision.code is RefusalCode.NO_AUTHORITY


@pytest.mark.asyncio
async def test_untrusted_content_escalates_a_write():
    g = guard()
    g.record_result(ToolResult(tool_name="search", server="tracker"))
    assert isinstance(await g.aauthorise(CREATE), NeedsApproval)


@pytest.mark.asyncio
async def test_the_configured_policy_still_applies():
    cfg = config(
        human_approval=HumanApprovalConfig(
            default_decision="allow",
            policies=[
                ApprovalPolicy(tools=["tracker.*"], decision="deny", reason="no")
            ],
        )
    )
    decision = await guard(cfg=cfg).aauthorise(CREATE)
    assert isinstance(decision, Refused)
    assert decision.code is RefusalCode.POLICY_DENIED


@pytest.mark.asyncio
async def test_each_decision_is_journalled_once():
    g = guard()
    await g.aauthorise(CREATE)
    await g.aauthorise(CREATE)
    assert len(g.journal.entries) == 2
