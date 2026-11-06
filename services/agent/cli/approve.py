"""Answering an approval from a terminal (E28-T5)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Callable

FALLBACK_DECISIONS = ("approve", "reject")


@dataclass(frozen=True)
class Answer:
    """A decision on an approval request, and anything said with it."""

    decision: str
    message: str = ""
    automatic: bool = False


def describe(request: dict[str, Any]) -> str:
    """One action, as a line somebody can decide on."""
    action = str(request.get("action") or "unknown")
    said = str(request.get("description") or "").strip()
    args = request.get("args") or {}
    shown = ", ".join(f"{k}={v!r}" for k, v in list(args.items())[:4])
    line = said or action
    return f"{line}\n    {action}({shown})" if shown else line


def is_interactive() -> bool:
    """Whether there is a person on both ends of this."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def decide(
    waiting: dict[str, Any],
    *,
    approve_all: bool = False,
    interactive: bool | None = None,
    ask: Callable[[str], str] | None = None,
    write: Callable[[str], None] | None = None,
) -> Answer | None:
    """What to send back, or `None` when nobody can be asked."""
    say = write or (lambda line: print(line, file=sys.stderr))
    requests = waiting.get("awaiting") or []
    allowed = tuple(
        (waiting.get("resume") or {}).get("decisions") or FALLBACK_DECISIONS
    )

    if approve_all:
        for one in requests:
            say(f"Approved without asking: {describe(one)}")
        return Answer("approve", automatic=True)

    if interactive is None:
        interactive = is_interactive()
    if not interactive:
        return None

    asking = ask or input
    for one in requests:
        say(describe(one))
    choice = asking(f"{_either(allowed)}? ").strip().lower()
    if choice not in allowed:
        say(f"{choice!r} is not one of {_either(allowed)}; nothing was sent.")
        return None
    if choice == "reject":
        return Answer("reject", message=asking("why? ").strip())
    return Answer(choice)


def _either(options: tuple[str, ...]) -> str:
    """The options rendered as `a, b or c`."""
    if len(options) < 2:
        return options[0] if options else "approve"
    return ", ".join(options[:-1]) + f" or {options[-1]}"


NOT_AUDITED = (
    "approval decisions are not written to the agent's audit trail — "
    "see services/agent/cli/approve.py"
)
