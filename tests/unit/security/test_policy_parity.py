"""The new grading must agree with the grading already in production."""

from __future__ import annotations

import pytest

from agent.src.agent.config.hitl import resolve_policy
from agent.src.agent.config.middleware import ApprovalPolicy, HumanApprovalConfig
from agent.src.security.policy import ConfigPolicySource
from agent.src.security.resolver import Identity, ToolCall

SOMEONE = Identity(subject="someone@example.com")

CONFIGS = {
    "defaults only": HumanApprovalConfig(),
    "default allow": HumanApprovalConfig(default_decision="allow"),
    "default deny": HumanApprovalConfig(default_decision="deny"),
    "exclusions": HumanApprovalConfig(exclude=["ls", "glob", "docs.*"]),
    "policies": HumanApprovalConfig(
        policies=[
            ApprovalPolicy(
                tools=["delete_*"], decision="deny", risk="high", reason="destructive"
            ),
            ApprovalPolicy(
                tools=["tracker.*"], decision="ask", risk="medium", reason="shared"
            ),
        ]
    ),
    "overlapping policies": HumanApprovalConfig(
        policies=[
            ApprovalPolicy(tools=["tracker.*"], decision="ask", reason="first"),
            ApprovalPolicy(
                tools=["tracker.create_issue"], decision="deny", reason="second"
            ),
        ]
    ),
    "exclusion overlapping a policy": HumanApprovalConfig(
        exclude=["docs.*"],
        policies=[
            ApprovalPolicy(tools=["docs.delete"], decision="deny", reason="destructive")
        ],
    ),
}

TOOLS = [
    "ls",
    "glob",
    "read_file",
    "docs.search",
    "docs.delete",
    "tracker.search",
    "tracker.create_issue",
    "delete_thread",
    "unheard_of_tool",
]


@pytest.mark.parametrize("name", sorted(CONFIGS))
@pytest.mark.parametrize("tool", TOOLS)
def test_grades_match_the_existing_resolution(name, tool):
    config = CONFIGS[name]
    expected = resolve_policy(tool, config)
    grade, risk, reason = ConfigPolicySource(config).decide(
        SOMEONE, ToolCall(name=tool)
    )
    assert grade == expected.decision
    assert risk == expected.risk
    assert reason == expected.reason


@pytest.mark.parametrize("name", sorted(CONFIGS))
@pytest.mark.parametrize("tool", TOOLS)
def test_the_whole_policy_matches_including_the_patterns_it_matched(name, tool):
    config = CONFIGS[name]
    assert ConfigPolicySource(config).policy_for(ToolCall(name=tool)) == resolve_policy(
        tool, config
    )


def test_there_is_only_one_implementation(monkeypatch):
    def explode(self, call):
        raise AssertionError("called")

    monkeypatch.setattr(ConfigPolicySource, "policy_for", explode)
    with pytest.raises(AssertionError, match="called"):
        resolve_policy("tracker.create_issue", CONFIGS["policies"])
