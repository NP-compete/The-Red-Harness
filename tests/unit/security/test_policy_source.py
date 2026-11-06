"""Resolving a tool to allow / ask / deny from the approval config."""

from __future__ import annotations

from agent.src.agent.config.middleware import ApprovalPolicy, HumanApprovalConfig
from agent.src.security.policy import ConfigPolicySource
from agent.src.security.resolver import Identity, ToolCall

SOMEONE = Identity(subject="someone@example.com")


def source(**kwargs) -> ConfigPolicySource:
    return ConfigPolicySource(HumanApprovalConfig(**kwargs))


def call(name: str) -> ToolCall:
    return ToolCall(name=name)


def test_first_matching_policy_wins():
    policies = [
        ApprovalPolicy(
            tools=["tracker.*"], decision="ask", risk="high", reason="shared tracker"
        ),
        ApprovalPolicy(tools=["tracker.create_issue"], decision="deny", reason="never"),
    ]
    assert source(policies=policies).decide(SOMEONE, call("tracker.create_issue")) == (
        "ask",
        "high",
        "shared tracker",
    )


def test_patterns_match_families_of_tools():
    policies = [
        ApprovalPolicy(tools=["delete_*"], decision="deny", reason="destructive")
    ]
    assert source(policies=policies).decide(SOMEONE, call("delete_thread"))[0] == "deny"
    assert source(policies=policies).decide(SOMEONE, call("read_thread"))[0] == "ask"


def test_unmatched_tool_takes_the_default_decision():
    assert (
        source(default_decision="deny").decide(SOMEONE, call("anything"))[0] == "deny"
    )


def test_default_decision_is_ask_when_unset():
    assert source().decide(SOMEONE, call("anything"))[0] == "ask"


def test_excluded_tools_are_allowed():
    assert source(exclude=["ls", "glob"]).decide(SOMEONE, call("ls"))[0] == "allow"


def test_exclude_accepts_patterns_like_policies_do():
    assert source(exclude=["docs.*"]).decide(SOMEONE, call("docs.search"))[0] == "allow"


def test_the_legacy_exclude_list_outranks_a_policy():
    policies = [
        ApprovalPolicy(tools=["docs.delete"], decision="deny", reason="destructive")
    ]
    decided = source(exclude=["docs.*"], policies=policies).decide(
        SOMEONE, call("docs.delete")
    )
    assert decided[0] == "allow"


def test_disabled_approval_allows_everything():
    assert (
        source(enabled=False, default_decision="deny").decide(SOMEONE, call("x"))[0]
        == "allow"
    )


def test_mode_none_allows_everything():
    assert (
        source(mode="none", default_decision="deny").decide(SOMEONE, call("x"))[0]
        == "allow"
    )


def test_an_unmatched_tool_says_it_fell_back_to_the_default():
    grade, risk, reason = source().decide(SOMEONE, call("anything"))
    assert grade == "ask"
    assert risk == "medium"
    assert "default_decision" in reason


def test_an_excluded_tool_says_why_it_was_allowed():
    _, _, reason = source(exclude=["ls"]).decide(SOMEONE, call("ls"))
    assert "Excluded" in reason
