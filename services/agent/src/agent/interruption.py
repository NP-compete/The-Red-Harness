"""What to do when someone speaks while the agent is still working."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

STOP_WORDS = ("stop", "cancel", "halt", "abort", "wait")
REDIRECT_WORDS = ("actually", "forget that", "instead", "never mind", "scrap that")
QUESTION_WORDS = ("what", "why", "how", "when", "where", "who", "is it", "are you")


class Handling(Enum):
    """What was done with an interruption."""

    FOLDED_IN = "folded-in"
    REDIRECTED = "redirected"
    STOPPED = "stopped"
    ANSWERED = "answered"
    IGNORED = "ignored"
    TOO_LATE = "too-late"


@dataclass(frozen=True)
class Running:
    """What the run was doing when it was interrupted."""

    stage: str
    tool: str
    reversible: bool
    steps_done: int


@dataclass(frozen=True)
class Interruption:
    """Something said while a run was going."""

    text: str
    urgent: bool

    def __post_init__(self) -> None:
        """Reject an interruption carrying no message."""
        if not self.text:
            raise ValueError("an interruption must carry a message")


@dataclass(frozen=True)
class Response:
    """How the interruption was handled, and whether the run goes on."""

    handling: Handling
    continues: bool
    keeps_work: bool
    applies_after_current_step: bool = False
    reason: str = ""


def handle(interruption: Interruption, *, running: Running) -> Response:
    """Decide what to do with `interruption` given what is `running`."""
    if running.stage == "done":
        return Response(
            Handling.TOO_LATE,
            continues=False,
            keeps_work=True,
            reason="this run had already finished",
        )

    said = interruption.text.strip().lower()
    if not said:
        return Response(Handling.IGNORED, continues=True, keeps_work=True)

    deferred = running.stage == "calling-tool" and not running.reversible

    if interruption.urgent or said.startswith(STOP_WORDS):
        return Response(
            Handling.STOPPED,
            continues=False,
            keeps_work=False,
            applies_after_current_step=deferred,
            reason=f"stopping after {running.steps_done} steps",
        )

    if any(word in said for word in REDIRECT_WORDS):
        return Response(
            Handling.REDIRECTED,
            continues=True,
            keeps_work=False,
            applies_after_current_step=deferred,
            reason=f"abandoning {running.steps_done} steps of work",
        )

    if said.endswith("?") or said.startswith(QUESTION_WORDS):
        return Response(Handling.ANSWERED, continues=True, keeps_work=True)

    return Response(Handling.FOLDED_IN, continues=True, keeps_work=True)
