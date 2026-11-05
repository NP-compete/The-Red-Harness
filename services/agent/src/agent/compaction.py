"""Decides which part of a conversation to summarise when it grows too long."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class Message:
    """One message in the history, and what it costs to keep."""

    role: str
    text: str
    tokens: int
    trusted: bool = True
    awaiting_approval: bool = False
    is_summary: bool = False
    is_skill: bool = False
    tool_call_id: str = ""


@dataclass(frozen=True)
class Plan:
    """Which messages to summarise away and which to keep."""

    summarise: list[Message] = field(default_factory=list)
    keep: list[Message] = field(default_factory=list)
    summary_is_trusted: bool = True


def _whole_exchanges_only(
    messages: list[Message], summarise: list[Message]
) -> list[Message]:
    """Drop any tool exchange that would be summarised only in part."""
    going = set(id(m) for m in summarise)
    half_gone = {
        m.tool_call_id for m in messages if m.tool_call_id and id(m) not in going
    }
    if not half_gone:
        return summarise
    return [m for m in summarise if m.tool_call_id not in half_gone]


def plan_compaction(
    messages: list[Message],
    *,
    limit_tokens: int,
    keep_recent: int = 2,
    trigger_at: float = 0.8,
) -> Plan | None:
    """Plan a compaction if the history is close to its limit."""
    used = sum(message.tokens for message in messages)
    if used < limit_tokens * trigger_at:
        return None

    recent = (
        set(id(m) for m in messages[len(messages) - keep_recent :])
        if keep_recent
        else set()
    )

    summarise = [
        m
        for m in messages
        if m.role != "system"
        and not m.is_skill
        and not m.awaiting_approval
        and id(m) not in recent
    ]
    summarise = _whole_exchanges_only(messages, summarise)
    if not summarise:
        return None

    summarised = set(id(m) for m in summarise)
    return Plan(
        summarise=summarise,
        keep=[m for m in messages if id(m) not in summarised],
        summary_is_trusted=all(m.trusted for m in summarise),
    )


def apply_compaction(
    messages: list[Message], plan: Plan | None, *, summary: str
) -> list[Message]:
    """Carry out `plan`, replacing the summarised messages with `summary`."""
    if plan is None:
        return messages
    if not summary.strip():
        raise ValueError("a summary is required to replace the messages it covers")

    replaced = set(id(m) for m in plan.summarise)
    first = min(messages.index(m) for m in plan.summarise)

    stand_in = Message(
        role="user",
        text=summary,
        tokens=len(summary.split()),
        trusted=plan.summary_is_trusted,
        is_summary=True,
    )

    out: list[Message] = []
    for index, message in enumerate(messages):
        if index == first:
            out.append(stand_in)
        if id(message) not in replaced:
            out.append(message)
    return out


async def shorten(
    messages: list[Message],
    *,
    limit_tokens: int,
    summarise: Callable[[list[Message]], Awaitable[str]],
    keep_recent: int = 2,
    timeout_seconds: float = TIMEOUT_SECONDS,
) -> list[Message]:
    """Replace the oldest exchanges with a summary, or change nothing."""
    plan = plan_compaction(messages, limit_tokens=limit_tokens, keep_recent=keep_recent)
    if plan is None:
        return messages

    try:
        summary = await asyncio.wait_for(
            summarise(plan.summarise), timeout=timeout_seconds
        )
    except TimeoutError:
        logger.warning("Summarising took too long; leaving the history as it was")
        return messages
    except Exception as error:
        logger.warning("Could not summarise (%s); leaving the history as it was", error)
        return messages

    if not summary or not summary.strip():
        logger.warning("The summary came back empty; leaving the history as it was")
        return messages

    try:
        return apply_compaction(messages, plan, summary=summary)
    except Exception as error:
        logger.warning("Could not apply the summary (%s); leaving it as it was", error)
        return messages


def can_be_wired() -> tuple[bool, str]:
    """Whether the graph's messages carry what the plan needs."""
    missing = ("awaiting_approval", "is_skill", "trusted")
    return (
        False,
        "the graph's messages carry no "
        + ", ".join(missing)
        + "; mapping them would mean guessing, and the plan refuses to "
        "summarise exactly those",
    )
