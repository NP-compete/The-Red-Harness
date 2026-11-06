"""Holds the per-run state the five stages share."""

from __future__ import annotations

from typing import Any

from agent.src.agent.config.middleware import ResolvedMiddlewareConfig
from agent.src.security.authority import CredentialAuthoritySource, Credentials
from agent.src.security.budget import RunBudget
from agent.src.security.delegation import DelegatedAuthoritySource, Delegation
from agent.src.security.fencing import fence
from agent.src.security.journal import DecisionJournal
from agent.src.security.policy import ConfigPolicySource
from agent.src.security.resolver import (
    AuthoritySource,
    Decision,
    Identity,
    Provenance,
    RunContext,
    ToolCall,
    resolve,
    resolve_async,
)
from agent.src.security.taint import TaintLedger
from agent.src.security.trust import RunTrust, ToolResult


def _authority(
    credentials: Credentials,
    servers: dict[str, dict[str, Any]],
    delegations: list[Delegation] | None,
) -> DelegatedAuthoritySource:
    """An authority source that honours delegations on top of credentials."""
    return DelegatedAuthoritySource(
        base=CredentialAuthoritySource(credentials, servers),
        delegations=delegations or [],
    )


class Guard:
    """The run-scoped front door to authorisation, budget and trust."""

    def __init__(
        self,
        *,
        identity: Identity,
        authority: AuthoritySource,
        policy: ConfigPolicySource,
        budget: RunBudget,
        trust: RunTrust,
        provenance: Provenance,
        trusted_servers: list[str],
        taint: TaintLedger | None = None,
    ) -> None:
        """Bind a guard to one run's identity, policy, budget and trust."""
        self._authority = authority
        self._policy = policy
        self._budget = budget
        self._trust = trust
        self._taint = taint
        self._trusted_servers = frozenset(trusted_servers)
        self._context = RunContext(identity=identity, provenance=provenance)
        self.journal = DecisionJournal()

    @property
    def context(self) -> RunContext:
        """The run context as it stands, with trust applied."""
        return self._trust.apply(self._context)

    @property
    def spent(self) -> tuple[int, int]:
        """Tool calls and tokens spent so far."""
        return self._budget.spent

    def authorise(self, call: ToolCall) -> Decision:
        """Decide whether `call` may proceed."""
        return resolve(
            self._context_for(call),
            call,
            authority=self._authority,
            policy=self._policy,
            budget=self._budget,
            journal=self.journal,
        )

    async def aauthorise(self, call: ToolCall) -> Decision:
        """Decide whether `call` may proceed, awaiting async sources."""
        return await resolve_async(
            self._context_for(call),
            call,
            authority=self._authority,
            policy=self._policy,
            budget=self._budget,
            journal=self.journal,
        )

    def record_call(self, call: ToolCall) -> None:
        """Charge `call` against the run's budget."""
        self._budget.record(call)

    def record_tokens(self, tokens: int) -> None:
        """Charge `tokens` against the run's budget."""
        self._budget.record_tokens(tokens)

    def ingest(self, result: ToolResult, *, text: str) -> str:
        """Record what a tool returned and hand back what the model may see."""
        self.record_result(result, text)
        if result.server is None or result.server in self._trusted_servers:
            return text
        return fence(text, source=result.server)

    def record_result(self, result: ToolResult, text: str = "") -> None:
        """Record what a tool returned, tainting the run if the server is untrusted."""
        self._trust.record(result)
        if (
            self._taint is not None
            and text
            and result.server not in self._trusted_servers
        ):
            self._taint.record(text)

    def _context_for(self, call: ToolCall) -> RunContext:
        """The context to judge `call` in, escalating on tainted writes."""
        if self._taint is None:
            return self.context
        if call.writes and self._taint.derives(call.args):
            return self._context.with_untrusted_read()
        return self._context


def build_guard(
    *,
    config: ResolvedMiddlewareConfig,
    credentials: Credentials,
    servers: dict[str, dict[str, Any]],
    identity: Identity,
    effects: str = "live",
    delegations: list[Delegation] | None = None,
    precise_taint: bool = False,
    token_limit: int | None = None,
    fingerprint: str = "",
    schema_version: int = 0,
) -> Guard:
    """Assemble a guard for one run from resolved config and credentials."""
    return Guard(
        identity=identity,
        authority=_authority(credentials, servers, delegations),
        policy=ConfigPolicySource(config.human_approval, effects=effects),
        budget=RunBudget(config.tool_call_limit, token_limit=token_limit),
        trust=RunTrust(config.tool_output.trusted_servers),
        trusted_servers=config.tool_output.trusted_servers,
        taint=TaintLedger() if precise_taint else None,
        provenance=Provenance(
            config_fingerprint=fingerprint, schema_version=schema_version
        ),
    )
