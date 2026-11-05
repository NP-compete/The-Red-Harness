"""The five stages working together on one run, with no stubbed stages."""

from __future__ import annotations

from agent.src.agent.config.middleware import (
    ApprovalPolicy,
    HumanApprovalConfig,
    ToolCallLimitConfig,
)
from agent.src.security.authority import CredentialAuthoritySource
from agent.src.security.budget import RunBudget
from agent.src.security.policy import ConfigPolicySource
from agent.src.security.resolver import (
    Allowed,
    Identity,
    NeedsApproval,
    RefusalCode,
    Refused,
    RunContext,
    ToolCall,
    resolve,
)
from agent.src.security.trust import RunTrust, ToolResult

SERVERS = {
    "tracker": {"url": "https://tracker.example"},
    "docs": {"url": "https://docs"},
}

SEARCH = ToolCall(name="tracker.search", server="tracker")
CREATE = ToolCall(name="tracker.create_issue", server="tracker", writes=True)


class ConnectedEverywhere:
    async def has_valid_token(self, user_id, mcp_name, server_cfg, *, verify=False):
        return True


def harness(*, per_tool=None):
    policy = ConfigPolicySource(
        HumanApprovalConfig(
            default_decision="allow",
            policies=[
                ApprovalPolicy(
                    tools=["tracker.create_issue"],
                    decision="allow",
                    risk="high",
                    reason="writes to a shared tracker.",
                )
            ],
        )
    )
    return {
        "authority": CredentialAuthoritySource(ConnectedEverywhere(), SERVERS),
        "policy": policy,
        "budget": RunBudget(ToolCallLimitConfig(run_limit=10, per_tool=per_tool or {})),
    }


def test_a_write_is_allowed_until_the_run_reads_something_untrusted():
    sources = harness()
    ctx = RunContext(identity=Identity(subject="someone@example.com"))

    assert isinstance(resolve(ctx, CREATE, **sources), Allowed)

    trust = RunTrust(trusted_servers=["docs"])
    trust.record(ToolResult(tool_name="search", server="tracker"))
    tainted = trust.apply(ctx)

    decision = resolve(tainted, CREATE, **sources)
    assert isinstance(decision, NeedsApproval)
    assert decision.risk == "high"
    assert "shared tracker" in decision.reason
    assert "outside system" in decision.reason


def test_reading_stays_allowed_after_the_run_is_tainted():
    sources = harness()
    trust = RunTrust(trusted_servers=["docs"])
    trust.record(ToolResult(tool_name="search", server="tracker"))
    ctx = trust.apply(RunContext(identity=Identity(subject="someone@example.com")))

    assert isinstance(resolve(ctx, SEARCH, **sources), Allowed)


def test_a_trusted_source_never_escalates_the_write():
    sources = harness()
    trust = RunTrust(trusted_servers=["docs", "tracker"])
    trust.record(ToolResult(tool_name="search", server="tracker"))
    ctx = trust.apply(RunContext(identity=Identity(subject="someone@example.com")))

    assert isinstance(resolve(ctx, CREATE, **sources), Allowed)


def test_a_per_tool_ceiling_refuses_before_approval_is_asked_for():
    sources = harness(per_tool={"tracker.create_issue": 1})
    ctx = RunContext(identity=Identity(subject="someone@example.com"))

    assert isinstance(resolve(ctx, CREATE, **sources), Allowed)
    sources["budget"].record(CREATE)

    decision = resolve(ctx, CREATE, **sources)
    assert isinstance(decision, Refused)
    assert decision.code is RefusalCode.BUDGET_EXHAUSTED


def test_an_unconnected_server_refuses_before_policy_is_consulted():
    sources = harness()
    sources["authority"] = CredentialAuthoritySource(ConnectedEverywhere(), servers={})
    ctx = RunContext(identity=Identity(subject="someone@example.com"))

    decision = resolve(ctx, CREATE, **sources)
    assert isinstance(decision, Refused)
    assert decision.code is RefusalCode.NO_AUTHORITY
