"""Noticing when a run is going round in circles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

REPEAT_LIMIT = 3
ALTERNATE_LIMIT = 6
FAILURE_LIMIT = 4
DEFAULT_WINDOW = 10
OK = "ok"


class Pattern(Enum):
    """What the recent tool calls look like."""

    PROGRESSING = "progressing"
    REPEATING = "repeating"
    ALTERNATING = "alternating"
    SAME_FAILURE = "same-failure"


@dataclass(frozen=True)
class Call:
    """One tool call and what it returned."""

    tool: str
    arguments: str = "{}"
    result: str = OK


@dataclass(frozen=True)
class Inspection:
    """Whether the run is looping, and whether to stop it."""

    pattern: Pattern
    should_stop: bool
    repeated: str = ""
    times: int = 0
    reason: str = ""


def inspect_calls(calls: list[Call], *, window: int = DEFAULT_WINDOW) -> Inspection:
    """Look at the last `window` calls for signs of a loop."""
    if window < 1:
        raise ValueError("there must be some calls to look at")

    recent = calls[-window:]

    run = _identical_run(recent)
    if run >= REPEAT_LIMIT:
        last = recent[-1]
        return Inspection(
            Pattern.REPEATING,
            should_stop=True,
            repeated=last.tool,
            times=run,
            reason=f"{last.tool} has been called {run} times with the same arguments",
        )

    if _alternating(recent):
        first, second = recent[-2].tool, recent[-1].tool
        return Inspection(
            Pattern.ALTERNATING,
            should_stop=True,
            repeated=f"{first}/{second}",
            times=ALTERNATE_LIMIT,
            reason=f"{first} and {second} are calling each other in turn",
        )

    failure = _same_failure(recent)
    if failure:
        return Inspection(
            Pattern.SAME_FAILURE,
            should_stop=True,
            repeated=recent[-1].tool,
            times=FAILURE_LIMIT,
            reason=f"the last {FAILURE_LIMIT} calls all returned: {failure}",
        )

    return Inspection(Pattern.PROGRESSING, should_stop=False)


def _key(call: Call) -> tuple[str, str]:
    """The tool and arguments that make a call the same as another."""
    return (call.tool, call.arguments)


def _identical_run(calls: list[Call]) -> int:
    """How many identical calls end the sequence."""
    if not calls:
        return 0
    last = _key(calls[-1])
    run = 0
    for call in reversed(calls):
        if _key(call) != last:
            break
        run += 1
    return run


def _alternating(calls: list[Call]) -> bool:
    """Whether the tail alternates between two calls."""
    if len(calls) < ALTERNATE_LIMIT:
        return False
    tail = [_key(call) for call in calls[-ALTERNATE_LIMIT:]]
    odd, even = tail[0::2], tail[1::2]
    return len(set(odd)) == 1 and len(set(even)) == 1 and odd[0] != even[0]


def _same_failure(calls: list[Call]) -> str:
    """The error every recent call returned, if they all did."""
    if len(calls) < FAILURE_LIMIT:
        return ""
    results = {call.result for call in calls[-FAILURE_LIMIT:]}
    if len(results) == 1 and (only := results.pop()) != OK:
        return only
    return ""
