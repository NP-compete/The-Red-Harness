"""What a subagent is told, and what it is not."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    """One piece of parent context that might go into a brief."""

    text: str
    kind: str
    trusted: bool
    relevant_to: tuple[str, ...]
    words: int

    def __post_init__(self) -> None:
        """Reject an empty item."""
        if self.words < 1:
            raise ValueError("an item must have something in it")


@dataclass(frozen=True)
class Brief:
    """What a subagent is being asked to do, and what it may be given."""

    task: str
    child_job: str
    budget_words: int
    parent_credentials: tuple[str, ...]
    child_may_use: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a brief with no task or no room for context."""
        if not self.task.strip():
            raise ValueError("a subagent must be given a task")
        if self.budget_words < 1:
            raise ValueError("a brief needs room for something")


@dataclass(frozen=True)
class Line:
    """One line of a built brief, and how it must be rendered."""

    text: str
    trusted: bool
    fenced: bool


@dataclass(frozen=True)
class Built:
    """The brief as actually assembled, and what was left out."""

    task: str
    job: str
    included: tuple[Line, ...]
    credentials: tuple[str, ...]
    words: int
    left_out: int


def build_brief(context: list[Item], *, brief: Brief) -> Built:
    """Assemble a subagent brief from parent context, within its budget."""
    beyond = set(brief.child_may_use) - set(brief.parent_credentials)
    if beyond:
        raise ValueError(f"the parent cannot pass on {', '.join(sorted(beyond))}")

    relevant = [item for item in context if brief.child_job in item.relevant_to]

    lines: list[Line] = []
    used = 0
    for item in relevant:
        if used + item.words > brief.budget_words:
            continue
        used += item.words
        lines.append(
            Line(
                text=item.text,
                trusted=item.trusted,
                fenced=not item.trusted,
            )
        )

    return Built(
        task=brief.task,
        job=brief.child_job,
        included=tuple(lines),
        credentials=tuple(brief.child_may_use),
        words=used,
        left_out=len(context) - len(lines),
    )
