"""Carrying out a request to forget something, and saying what that cannot undo."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Held:
    """One memory held about someone, and how far it has spread."""

    key: str
    text: str
    topic: str
    owner: str
    used_in_sent_message: bool
    shared_with_team: bool


@dataclass(frozen=True)
class Plan:
    """What forgetting would remove, and what it cannot take back."""

    forgetting: list[str]
    untouched: list[str]
    cannot_unsay: list[str]
    affects_others: list[str]

    @property
    def found_nothing(self) -> bool:
        """Whether nothing matched the request."""
        return not self.forgetting

    @property
    def needs_confirmation(self) -> bool:
        """Whether forgetting would affect anyone else."""
        return bool(self.affects_others)


def plan_forget(memories: list[Held], *, asked_by: str, about: str) -> Plan:
    """Plan what to forget about `about` on behalf of `asked_by`."""
    if not asked_by.strip():
        raise ValueError("a request must come from someone")

    wanted = about.strip().lower()

    forgetting: list[str] = []
    untouched: list[str] = []
    cannot_unsay: list[str] = []
    affects_others: list[str] = []
    for memory in memories:
        if wanted and wanted not in (memory.key.lower(), memory.topic.lower()):
            continue
        if memory.owner != asked_by:
            untouched.append(memory.key)
            continue
        forgetting.append(memory.key)
        if memory.used_in_sent_message:
            cannot_unsay.append(memory.key)
        if memory.shared_with_team:
            affects_others.append(memory.key)

    return Plan(
        forgetting=forgetting,
        untouched=untouched,
        cannot_unsay=cannot_unsay,
        affects_others=affects_others,
    )
