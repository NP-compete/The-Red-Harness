"""The single place a tool call is authorised."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:  # pragma: no cover - typing only
    from agent.src.security.journal import Entry

__all__ = [
    "Allowed",
    "Budget",
    "Decision",
    "Effects",
    "Identity",
    "NeedsApproval",
    "Provenance",
    "RefusalCode",
    "Refused",
    "RunContext",
    "ToolCall",
    "Trust",
    "Unavailable",
    "resolve",
    "resolve_async",
]


class Trust(str, Enum):
    """How far the content a run has already read can be trusted."""

    CLEAN = "clean"
    UNTRUSTED_READ = "untrusted_read"


class Effects(str, Enum):
    """Whether a run's tool calls really happen or are only rehearsed."""

    LIVE = "live"
    DRY_RUN = "dry_run"


class RefusalCode(str, Enum):
    """Why a tool call was refused."""

    NO_AUTHORITY = "no_authority"
    POLICY_DENIED = "policy_denied"
    BUDGET_EXHAUSTED = "budget_exhausted"


@dataclass(frozen=True)
class Identity:
    """Who is making a call, and on whose behalf."""

    subject: str
    groups: tuple[str, ...] = ()
    delegated_by: str | None = None


@dataclass(frozen=True)
class Budget:
    """What a run has left to spend."""

    tokens_remaining: int | None = None
    calls_remaining: int | None = None


@dataclass(frozen=True)
class Provenance:
    """Which config and resolver version produced a decision."""

    config_fingerprint: str = ""
    schema_version: int = 0
    resolver_version: str = "1"


@dataclass(frozen=True)
class RunContext:
    """Everything about a run that bears on whether a call is allowed."""

    identity: Identity | None
    trust: Trust = Trust.CLEAN
    effects: Effects = Effects.LIVE
    budget: Budget = field(default_factory=Budget)
    provenance: Provenance = field(default_factory=Provenance)

    def with_untrusted_read(self) -> "RunContext":
        """This context, marked as having read untrusted content."""
        if self.trust is Trust.UNTRUSTED_READ:
            return self
        return replace(self, trust=Trust.UNTRUSTED_READ)


@dataclass(frozen=True)
class ToolCall:
    """A single tool invocation being judged."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)
    writes: bool = False
    server: str | None = None


@dataclass(frozen=True)
class Allowed:
    """The call may proceed."""

    ctx: RunContext


@dataclass(frozen=True)
class NeedsApproval:
    """The call needs a human to approve it first."""

    risk: Literal["low", "medium", "high"]
    reason: str
    scope: Literal["once", "run", "thread"] = "once"


@dataclass(frozen=True)
class Refused:
    """The call will not be made, with the reason and a way forward."""

    code: RefusalCode
    message: str
    remedy: str


@dataclass(frozen=True)
class Unavailable:
    """No decision could be reached because a dependency was down."""

    dependency: str
    retry_after_s: int | None = None


Decision = Allowed | NeedsApproval | Refused | Unavailable


class AuthoritySource(Protocol):
    """Answers whether an identity holds the authority for a call."""

    def holds(self, identity: Identity, call: ToolCall) -> bool | None:
        """None when the source could not be reached."""


class PolicySource(Protocol):
    """Answers what policy says about a call."""

    def decide(
        self, identity: Identity, call: ToolCall
    ) -> (
        tuple[Literal["allow", "ask", "deny"], Literal["low", "medium", "high"], str]
        | None
    ):
        """(grade, risk, reason), or None when unreachable."""


class Journal(Protocol):
    """Records the decisions the resolver reaches."""

    def record(self, entry: Any) -> None:
        """Record one decision."""
        ...


class BudgetSource(Protocol):
    """Answers what a run has left to spend."""

    def remaining(self, ctx: RunContext, call: ToolCall | None = None) -> Budget | None:
        """None when the accounting store could not be reached."""


_ESCALATION_NOTE = (
    "This run has read content from an outside system, "
    "so changes are confirmed with you first."
)


def resolve(
    ctx: RunContext,
    call: ToolCall,
    *,
    authority: AuthoritySource,
    policy: PolicySource,
    budget: BudgetSource,
    journal: "Journal | None" = None,
) -> Decision:
    """Decide whether `call` may proceed, and journal the decision."""
    decision = _resolve(ctx, call, authority=authority, policy=policy, budget=budget)
    if journal is not None:
        journal.record(_entry(ctx, call, decision))
    return decision


def _resolve(
    ctx: RunContext,
    call: ToolCall,
    *,
    authority: AuthoritySource,
    policy: PolicySource,
    budget: BudgetSource,
) -> Decision:
    """Reach a decision about `call` without journalling it."""
    if ctx.identity is None:
        return Unavailable(dependency="identity-provider")

    held = authority.holds(ctx.identity, call)
    if held is None:
        return Unavailable(dependency="secret-source")
    if not held:
        target = call.server or call.name
        return Refused(
            code=RefusalCode.NO_AUTHORITY,
            message=f"You have not connected {target}.",
            remedy=f"Connect {target} and run this again.",
        )

    decided = policy.decide(ctx.identity, call)
    if decided is None:
        return Refused(
            code=RefusalCode.POLICY_DENIED,
            message="The policy engine is unavailable, so this call is refused.",
            remedy="Retry once the policy engine is reachable.",
        )
    grade, risk, reason = decided

    if grade == "deny":
        return Refused(
            code=RefusalCode.POLICY_DENIED,
            message=reason or f"Policy denies {call.name}.",
            remedy="Ask an administrator to change the approval policy for this tool.",
        )

    escalated = call.writes and ctx.trust is Trust.UNTRUSTED_READ

    left = budget.remaining(ctx, call)
    if left is not None:
        exhausted = (
            left.tokens_remaining is not None and left.tokens_remaining <= 0
        ) or (left.calls_remaining is not None and left.calls_remaining <= 0)
        if exhausted:
            return Refused(
                code=RefusalCode.BUDGET_EXHAUSTED,
                message="This run has used its budget.",
                remedy="Start a new run, or ask an administrator to raise the budget.",
            )

    if grade == "ask" or escalated:
        return NeedsApproval(
            risk=risk,
            reason=f"{reason} {_ESCALATION_NOTE}".strip() if escalated else reason,
        )

    return Allowed(ctx=ctx)


async def resolve_async(
    ctx: RunContext,
    call: ToolCall,
    *,
    authority: AuthoritySource,
    policy: PolicySource,
    budget: BudgetSource,
    journal: "Journal | None" = None,
) -> Decision:
    """Same five questions, for callers already inside an event loop."""
    ask = getattr(authority, "aholds", authority.holds)
    held = ask(ctx.identity, call) if ctx.identity else None
    if inspect.isawaitable(held):
        held = await held

    return resolve(
        ctx,
        call,
        authority=_Settled(held),
        policy=policy,
        budget=budget,
        journal=journal,
    )


@dataclass(frozen=True)
class _Settled:
    """An authority source that always gives the same answer."""

    answer: bool | None

    def holds(self, identity: Identity, call: ToolCall) -> bool | None:
        """The settled answer, whatever the identity and call."""
        return self.answer


def _entry(ctx: RunContext, call: ToolCall, decision: Decision) -> "Entry":
    """Turn a decision into the journal entry that records it."""
    from agent.src.security.journal import Entry

    outcomes: dict[
        type, Literal["allowed", "needs_approval", "refused", "unavailable"]
    ] = {
        Allowed: "allowed",
        NeedsApproval: "needs_approval",
        Refused: "refused",
        Unavailable: "unavailable",
    }
    return Entry(
        subject=ctx.identity.subject if ctx.identity else "",
        tool=call.name,
        outcome=outcomes[type(decision)],
        trust=ctx.trust,
        config_fingerprint=ctx.provenance.config_fingerprint,
        schema_version=ctx.provenance.schema_version,
        resolver_version=ctx.provenance.resolver_version,
        code=getattr(decision, "code", None),
        dependency=getattr(decision, "dependency", None),
    )
