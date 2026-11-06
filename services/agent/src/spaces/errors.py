"""What a space surface refuses, and why."""

from __future__ import annotations


class SpaceNotFound(LookupError):
    """No such space — or none this person may see."""


class SpaceRefused(ValueError):
    """A space that cannot be created as asked."""
