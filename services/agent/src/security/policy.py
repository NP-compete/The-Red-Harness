"""Grades a tool call from the agent's approval configuration."""

from __future__ import annotations

from fnmatch import fnmatch
from typing import Literal

from agent.src.agent.config.middleware import ApprovalPolicy, HumanApprovalConfig
from agent.src.security.resolver import Identity, ToolCall

Grade = Literal["allow", "ask", "deny"]

_EXCLUDED_REASON = "Excluded from approval in config"
_DISABLED_REASON = "Approval is switched off for this agent"
_NO_MATCH_REASON = "No matching policy; using default_decision"


class ConfigPolicySource:
    """Approval policy read from the agent's configuration."""

    def __init__(self, config: HumanApprovalConfig, effects: str = "live") -> None:
        """Bind to `config`, judging calls under `effects`."""
        self._config = config
        self._effects = effects

    def decide(
        self, identity: Identity, call: ToolCall
    ) -> tuple[Grade, Literal["low", "medium", "high"], str] | None:
        """What policy says about `call`: the grade, risk and reason."""
        policy = self.policy_for(call)
        return (policy.decision, policy.risk, policy.reason)

    def policy_for(self, call: ToolCall) -> ApprovalPolicy:
        """The policy for `call`, with dry-run folded in."""
        policy = self._live_policy_for(call)

        if self._effects == "dry_run" and policy.decision == "ask":
            return ApprovalPolicy(
                tools=policy.tools,
                decision="deny",
                risk=policy.risk,
                reason=f"dry run — would have asked ({policy.reason or 'no reason given'})",
            )
        return policy

    def _live_policy_for(self, call: ToolCall) -> ApprovalPolicy:
        """The policy for `call` as configured, before dry-run is applied."""
        config = self._config

        if not config.enabled or config.mode == "none":
            return ApprovalPolicy(
                tools=[call.name], decision="allow", risk="low", reason=_DISABLED_REASON
            )

        for pattern in config.exclude:
            if fnmatch(call.name, pattern):
                return ApprovalPolicy(
                    tools=[pattern],
                    decision="allow",
                    risk="low",
                    reason=_EXCLUDED_REASON,
                )

        for policy in config.policies:
            if any(fnmatch(call.name, pattern) for pattern in policy.tools):
                return policy

        return ApprovalPolicy(
            tools=[call.name], decision=config.default_decision, reason=_NO_MATCH_REASON
        )
