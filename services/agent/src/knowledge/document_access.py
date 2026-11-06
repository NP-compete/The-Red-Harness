"""Dropping what the asker may not read before an answer is written."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hit:
    """One retrieved chunk, with who may read and who may merely see it."""

    chunk: str
    document: str
    readers: tuple[str, ...]
    listable_by: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a hit nobody is allowed to read."""
        if not self.readers:
            raise ValueError("a document nobody may read should not be indexed")


@dataclass(frozen=True)
class Asker:
    """Who is searching, and the groups they bring."""

    person: str
    groups: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject an asker who is nobody."""
        if not self.person.strip():
            raise ValueError("an asker must be someone")

    @property
    def identities(self) -> set[str]:
        """The person and their groups, as one set to match against."""
        return {self.person, *self.groups}


@dataclass(frozen=True)
class Filtered:
    """Search hits split into what the asker may use, and what was held back."""

    usable: list[str]
    withheld: int
    requestable: list[str]

    @property
    def nothing_left(self) -> bool:
        """Whether everything was withheld and nothing usable remains."""
        return self.withheld > 0 and not self.usable


def filter_hits(hits: list[Hit], *, asker: Asker) -> Filtered:
    """Split `hits` into what `asker` may read and what they may only request."""
    who = asker.identities

    usable: list[str] = []
    withheld = 0
    requestable: list[str] = []
    for hit in hits:
        if who & set(hit.readers):
            usable.append(hit.chunk)
            continue
        withheld += 1
        if who & set(hit.listable_by) and hit.document not in requestable:
            requestable.append(hit.document)

    return Filtered(usable=usable, withheld=withheld, requestable=requestable)
