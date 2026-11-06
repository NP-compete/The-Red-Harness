"""What a proposal would have done to the runs that motivated it (E12-T4)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Probed:
    """What reading more conversations said about a proposed change."""

    change: str
    touched: int = 0
    used: int = 0
    runs: list[str] = field(default_factory=list)
    verdict: str = ""
    rerun: bool = False


_ADDED_TOOL = re.compile(r"^\+\s*-\s*(\S+)\s*$", re.M)


def tool_withdrawn_by(diff: str) -> str:
    """The tool a diff would stop offering, if that is what it does."""
    found = _ADDED_TOOL.findall(diff or "")
    return found[0] if len(found) == 1 else ""


def probe(proposal: Any, runs: list[Any]) -> Probed | None:
    """Weigh one proposal against the conversations behind it."""
    name = tool_withdrawn_by(getattr(proposal, "diff", "") or "")
    if not name:
        return None

    touched = 0
    used = 0
    where: list[str] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        calls, helpful = _calls_to(name, run.get("messages") or [])
        if calls:
            touched += calls
            used += helpful
            where.append(str(run.get("run_id") or ""))

    return Probed(
        change=f"{name} is no longer offered",
        touched=touched,
        used=used,
        runs=where,
        verdict=_verdict(name, touched, used),
    )


def _verdict(name: str, touched: int, used: int) -> str:
    """The sentence explaining what the probe found."""
    if touched == 0:
        return (
            f"No call to {name} in the conversations read here, which "
            "disagrees with the observation that produced this. Widen the "
            "window before acting on it."
        )
    if used == 0:
        return (
            f"{name} was called {touched} time(s) in these conversations and "
            "no answer drew on any of them. Withdrawing it costs nothing "
            "visible in this window."
        )
    return (
        f"{name} was called {touched} time(s) here and {used} of those fed "
        "an answer. Withdrawing it takes those answers away too — this is "
        "a proposal to refuse unless something else can produce them."
    )


def _calls_to(name: str, messages: list[Any]) -> tuple[int, int]:
    """How often a tool answered, and how often the answer was used."""
    from agent.src.improvement.mine import _mentions, _text_of

    calls = 0
    used = 0
    for index, message in enumerate(messages):
        if not isinstance(message, dict) or message.get("type") != "tool":
            continue
        if str(message.get("name") or "") != name:
            continue
        calls += 1
        content = _text_of(message.get("content"))
        after = " ".join(
            _text_of(later.get("content"))
            for later in messages[index + 1 :]
            if isinstance(later, dict) and later.get("type") == "ai"
        )
        if content.strip() and after.strip() and _mentions(after, content):
            used += 1
    return calls, used
