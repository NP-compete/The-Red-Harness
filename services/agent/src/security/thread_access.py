"""Who may open a conversation, and what they may do with it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

VISIBILITIES = {"private", "team", "org"}


class Level(IntEnum):
    """How far someone may go with a thread."""

    NONE = 0
    READ = 1
    WRITE = 2


@dataclass(frozen=True)
class Thread:
    """A thread's owner, visibility and share link."""

    owner: str
    org: str
    team: str
    visibility: str
    share_link: str = ""
    share_expires_at: datetime | None = None
    held_by: str = ""

    def __post_init__(self) -> None:
        """Reject an unknown visibility or a share link that never expires."""
        if self.visibility not in VISIBILITIES:
            raise ValueError(f"{self.visibility} is not a visibility")
        if self.share_link and self.share_expires_at is None:
            raise ValueError("a share link must expire")


@dataclass(frozen=True)
class Viewer:
    """Who is looking, and the share link they came with."""

    person: str
    org: str
    teams: tuple[str, ...]
    link: str = ""


@dataclass(frozen=True)
class Access:
    """The level a viewer gets, and why."""

    level: Level
    reason: str = ""


def access_for(thread: Thread, viewer: Viewer, *, now: datetime) -> Access:
    """Work out what `viewer` may do with `thread` as of `now`."""
    level = _membership(thread, viewer)

    if _link_holds(thread, viewer, now=now):
        level = max(level, Level.READ)

    if level is Level.NONE:
        return Access(Level.NONE, "this conversation is not shared with you")

    if thread.held_by and thread.held_by != viewer.person:
        return Access(
            min(level, Level.READ), f"{thread.held_by} is working in this now"
        )

    return Access(level)


def _membership(thread: Thread, viewer: Viewer) -> Level:
    """The level `viewer` gets from org, ownership and team alone."""
    if viewer.org != thread.org:
        return Level.NONE
    if viewer.person == thread.owner:
        return Level.WRITE
    if thread.visibility == "org":
        return Level.READ
    if thread.visibility == "team" and thread.team in viewer.teams:
        return Level.READ
    return Level.NONE


def _link_holds(thread: Thread, viewer: Viewer, *, now: datetime) -> bool:
    """Whether the viewer's share link is this thread's and still live."""
    return bool(
        thread.share_link
        and viewer.link == thread.share_link
        and thread.share_expires_at is not None
        and now < thread.share_expires_at
    )
