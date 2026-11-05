"""What a deployment's own code may say about a request (E37-T1, T2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HookPoint(str, Enum):
    """Where in a turn an extension may be asked."""

    BEFORE_MODEL = "before_model"
    AFTER_MODEL = "after_model"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"


@dataclass(frozen=True)
class Payload:
    """Everything an extension may see."""

    text: str
    tool: str | None = None
    subject: str | None = None
    point: HookPoint = HookPoint.BEFORE_MODEL

    def as_json(self) -> dict[str, object]:
        """The wire form, for an extension in another process."""
        return {
            "point": self.point.value,
            "text": self.text,
            "tool": self.tool,
            "subject": self.subject,
        }


@dataclass(frozen=True)
class Unchanged:
    """It looked and had nothing to say."""


@dataclass(frozen=True)
class Rewritten:
    """It changed the text; this is what to use instead."""

    text: str


@dataclass(frozen=True)
class Refused:
    """It says this must not proceed, and why."""

    reason: str


Outcome = Unchanged | Rewritten | Refused

VERDICTS: dict[str, type] = {
    "unchanged": Unchanged,
    "rewritten": Rewritten,
    "refused": Refused,
}


def read_outcome(body: object) -> Outcome | None:
    """One reply, as an outcome — or `None` if it is not one."""
    if not isinstance(body, dict):
        return None
    verdict = str(body.get("verdict", "")).strip().lower()
    if verdict == "unchanged":
        return Unchanged()
    if verdict == "rewritten":
        text = body.get("text")
        return Rewritten(text=text) if isinstance(text, str) else None
    if verdict == "refused":
        return Refused(reason=str(body.get("reason") or "no reason given"))
    return None
