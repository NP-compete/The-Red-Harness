"""What is worth doing first in an empty workspace."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

UNDER_WAY_THREADS = 3


class Step(Enum):
    """One thing a new workspace could usefully do next."""

    CONNECT_SOURCE = "connect_source"
    ASK_SOMETHING = "ask_something"
    INVITE_OTHERS = "invite_others"


@dataclass(frozen=True)
class Workspace:
    """What a workspace has so far, and what its owner may do."""

    threads: int
    sources_connected: int
    memories: int
    members: int
    may_connect_sources: bool
    may_invite: bool
    dismissed: tuple[Step, ...]

    def __post_init__(self) -> None:
        """Reject negative counts, or a workspace with no members."""
        if min(self.threads, self.sources_connected, self.memories) < 0:
            raise ValueError("a workspace cannot hold less than nothing")
        if self.members < 1:
            raise ValueError("a workspace has at least one member")


def next_steps(workspace: Workspace) -> list[Step]:
    """The steps worth suggesting to this workspace."""
    working = workspace.threads >= UNDER_WAY_THREADS and workspace.sources_connected > 0

    wanted = []
    if workspace.sources_connected == 0 and workspace.may_connect_sources:
        wanted.append(Step.CONNECT_SOURCE)
    if workspace.threads == 0:
        wanted.append(Step.ASK_SOMETHING)
    if working and workspace.members == 1 and workspace.may_invite:
        wanted.append(Step.INVITE_OTHERS)

    return [step for step in wanted if step not in workspace.dismissed]
