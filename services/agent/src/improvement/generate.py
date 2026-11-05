"""Turning an observation into a configuration change somebody can read (E12-T3)."""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any

MAX_PER_RUN = 5

MIN_SEEN = 3

AGENT_CONFIG = "config/agent/runtime/agent.yaml"

STALE_AFTER_DAYS = 14


@dataclass(frozen=True)
class Proposal:
    """One proposed change, its argument, and the diff it would make."""

    kind: str
    detail: str
    argument: str
    seen: int = 0
    runs: list[str] = field(default_factory=list)
    path: str = ""
    diff: str = ""
    permitted: bool = True
    refusal: str = ""
    blocked: str = ""
    probe: Any = None


def generate(
    observations: list[Any],
    *,
    config_text: str,
    max_per_run: int = MAX_PER_RUN,
    stale_after_days: int = STALE_AFTER_DAYS,
    now: Any = None,
) -> list[Proposal]:
    """Proposals for the observations that imply one, most frequent first."""
    out: list[Proposal] = []
    for observation in observations:
        kind = str(getattr(observation, "kind", "") or "")
        rule = _RULES.get(kind)
        if rule is None:
            continue
        stale = _stale(observation, stale_after_days, now)
        if stale:
            out.append(_no_diff(_base(observation), stale))
            if len(out) >= max_per_run:
                break
            continue
        made = rule(observation, config_text)
        if made is not None:
            out.append(made)
        if len(out) >= max_per_run:
            break
    return out


def _abandoned_tool(observation: Any, config_text: str) -> Proposal | None:
    """A tool whose answer keeps going unused is a tool to stop offering."""
    seen = int(getattr(observation, "seen", 0) or 0)
    detail = str(getattr(observation, "detail", "") or "")
    name = detail.split(" ", 1)[0].strip()
    base = _base(observation)

    if seen < MIN_SEEN:
        return None
    if not name:
        return _no_diff(base, "the observation does not name a tool")

    after = _exclude_tool(config_text, name)
    if after is None:
        return _no_diff(
            base,
            f"{name} is already excluded, or this configuration has no "
            "tool_exclusion list to add it to",
        )

    argument = (
        f"{name} was called and its result went unused in {seen} run(s). "
        "Excluding it removes a tool the model is not using well; it stays "
        "in the configuration, commented by this list, so putting it back "
        "is one line."
    )
    return _checked(
        base,
        argument=argument,
        before={"middleware": {"tool_exclusion": {"tools": _excluded(config_text)}}},
        after={"middleware": {"tool_exclusion": {"tools": _excluded(after)}}},
        diff=_diff(config_text, after),
    )


def _spent_budget(observation: Any, config_text: str) -> Proposal | None:
    """The one edit this signal implies is one the loop may not make."""
    base = _base(observation)
    current = _run_limit(config_text)
    if current is None:
        return _no_diff(base, "this configuration sets no model call limit")

    argument = (
        f"Runs are ending at the call limit of {current}. The mechanical "
        "response is to raise it, which this loop may not propose: a "
        "runaway guard that moves whenever something hits it is not a "
        "guard. A person decides this one."
    )
    proposed = current * 2
    return _checked(
        base,
        argument=argument,
        before={"middleware": {"model_call_limit": {"run_limit": current}}},
        after={"middleware": {"model_call_limit": {"run_limit": proposed}}},
        diff=_diff(
            config_text,
            config_text.replace(f"run_limit: {current}", f"run_limit: {proposed}", 1),
        ),
    )


def _needs_words(observation: Any, _config_text: str) -> Proposal | None:
    """Real, and not fixable by any rule in this file."""
    return _no_diff(
        _base(observation),
        "the fix for this is wording in a prompt, and nothing here can "
        "write words. A generated sentence that reads plausibly is the "
        "one a reviewer approves without checking.",
    )


_RULES = {
    "tool_abandoned": _abandoned_tool,
    "budget_spent": _spent_budget,
    "repeated_question": _needs_words,
    "empty_delegation": _needs_words,
}


def _stale(observation: Any, after_days: int, now: Any) -> str:
    """Why this observation is too old to act on, or nothing."""
    from datetime import datetime, timedelta, timezone

    last = str(getattr(observation, "last_seen", "") or "")
    if not last or after_days <= 0:
        return ""
    try:
        when = datetime.fromisoformat(last.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if not when.tzinfo:
        when = when.replace(tzinfo=timezone.utc)
    today = now or datetime.now(timezone.utc)
    if when >= today - timedelta(days=after_days):
        return ""
    return (
        f"last seen {last}, more than {after_days} days ago. A proposal "
        "from traces older than the build cannot say whether it is still "
        "happening, and re-fixing something already fixed is how a "
        "reviewer learns to skim."
    )


def _base(observation: Any) -> Proposal:
    """The proposal an observation starts as, before any diff."""
    return Proposal(
        kind=str(getattr(observation, "kind", "") or ""),
        detail=str(getattr(observation, "detail", "") or ""),
        argument="",
        seen=int(getattr(observation, "seen", 0) or 0),
        runs=list(getattr(observation, "runs", []) or []),
        path=AGENT_CONFIG,
    )


def _no_diff(base: Proposal, why: str) -> Proposal:
    """`base` marked as blocked, with no diff."""
    from dataclasses import replace

    return replace(base, blocked=why, path="")


def _checked(
    base: Proposal, *, argument: str, before: Any, after: Any, diff: str
) -> Proposal:
    """Run the control rule, and record the verdict either way."""
    from dataclasses import replace

    from agent.src.improvement.propose import may_propose
    from agent.src.improvement.record import record_proposal

    verdict = may_propose(before=before, after=after)
    record_proposal(
        before=before,
        after=after,
        permitted=verdict.permitted,
        reason=verdict.reason,
        source="improvement.generate",
    )
    return replace(
        base,
        argument=argument,
        diff=diff if verdict.permitted else "",
        permitted=verdict.permitted,
        refusal=verdict.reason,
    )


def _diff(before: str, after: str) -> str:
    """A unified diff from `before` to `after`, or an empty string."""
    if before == after:
        return ""
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{AGENT_CONFIG}",
            tofile=f"b/{AGENT_CONFIG}",
            n=3,
        )
    )


_EXCLUSION = "tool_exclusion:"
_TOOLS = "tools:"


def _exclusion_block(lines: list[str]) -> tuple[int, int] | None:
    """Where `tool_exclusion.tools` starts and ends, by indentation."""
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == _EXCLUSION), None
    )
    if start is None:
        return None
    outer = len(lines[start]) - len(lines[start].lstrip())

    tools = None
    for i in range(start + 1, len(lines)):
        indent = len(lines[i]) - len(lines[i].lstrip())
        if lines[i].strip() and indent <= outer:
            break
        if lines[i].strip() == _TOOLS:
            tools = i
            break
    if tools is None:
        return None

    end = tools + 1
    while end < len(lines) and lines[end].lstrip().startswith("- "):
        end += 1
    return tools, end


def _excluded(text: str) -> list[str]:
    """The tools listed in the exclusion block of `text`."""
    lines = text.splitlines(keepends=True)
    found = _exclusion_block(lines)
    if found is None:
        return []
    tools, end = found
    return [lines[i].strip()[2:].strip() for i in range(tools + 1, end)]


def _exclude_tool(text: str, name: str) -> str | None:
    """The same file with one more tool excluded, or None."""
    lines = text.splitlines(keepends=True)
    found = _exclusion_block(lines)
    if found is None:
        return None
    tools, end = found
    if name in _excluded(text):
        return None

    indent = " " * (len(lines[tools]) - len(lines[tools].lstrip()) + 2)
    lines.insert(end, f"{indent}- {name}\n")
    return "".join(lines)


def _run_limit(text: str) -> int | None:
    """The run limit declared in `text`, if there is one."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("run_limit:"):
            try:
                return int(stripped.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None
