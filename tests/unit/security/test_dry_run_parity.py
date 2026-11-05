"""Dry run must mean the same thing in both resolution paths."""

from __future__ import annotations

import pytest

from agent.src.agent.config.hitl import resolve_policy
from agent.src.agent.config.middleware import ApprovalPolicy, HumanApprovalConfig
from agent.src.security.policy import ConfigPolicySource
from agent.src.security.resolver import Identity, ToolCall

SOMEONE = Identity(subject="someone@example.com")

CONFIG = HumanApprovalConfig(
    default_decision="ask",
    exclude=["ls"],
    policies=[
        ApprovalPolicy(tools=["docs.*"], decision="allow", reason="read only"),
        ApprovalPolicy(tools=["delete_*"], decision="deny", reason="destructive"),
        ApprovalPolicy(tools=["tracker.*"], decision="ask", reason="shared"),
    ],
)

TOOLS = [
    "ls",
    "docs.search",
    "delete_thread",
    "tracker.create_issue",
    "unheard_of_tool",
]


@pytest.mark.parametrize("tool", TOOLS)
def test_dry_run_grades_match_the_existing_resolution(tool):
    expected = resolve_policy(tool, CONFIG, effects="dry_run")
    grade, risk, reason = ConfigPolicySource(CONFIG, effects="dry_run").decide(
        SOMEONE, ToolCall(name=tool)
    )
    assert grade == expected.decision
    assert risk == expected.risk
    assert reason == expected.reason


def test_dry_run_turns_an_approval_into_a_refusal():
    grade, _, reason = ConfigPolicySource(CONFIG, effects="dry_run").decide(
        SOMEONE, ToolCall(name="tracker.create_issue")
    )
    assert grade == "deny"
    assert "dry run" in reason


def test_dry_run_leaves_an_allowed_tool_alone():
    grade, _, _ = ConfigPolicySource(CONFIG, effects="dry_run").decide(
        SOMEONE, ToolCall(name="docs.search")
    )
    assert grade == "allow"


def test_live_is_the_default():
    grade, _, _ = ConfigPolicySource(CONFIG).decide(
        SOMEONE, ToolCall(name="tracker.create_issue")
    )
    assert grade == "ask"
