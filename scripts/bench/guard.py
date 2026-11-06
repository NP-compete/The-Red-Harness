"""Not running a suite against an agent that can change things."""

from __future__ import annotations

SAFE = ("dry_run",)


class BenchRefused(RuntimeError):
    """The agent on the other end is not safe to measure against."""


def check_safe_to_run(*, effects: str | None) -> None:
    """Raise unless the agent cannot change anything."""
    if effects in SAFE:
        return None

    if not effects:
        raise BenchRefused(
            "could not tell whether this agent can change things "
            "(execution.effects was not reported). Refusing rather than assuming."
        )

    raise BenchRefused(
        f"this agent runs with execution.effects set to {effects!r}. "
        f"A suite is thousands of tool calls nobody wrote with your systems "
        f"in mind. Point it at an agent set to dry_run."
    )
