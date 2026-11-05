"""Deciding which written guidance a conversation picks up."""

from __future__ import annotations

from dataclasses import dataclass

_SCOPES = ("agent", "team", "user")


@dataclass(frozen=True)
class Skill:
    """One skill and the scope it is offered in."""

    name: str
    scope: str
    owner: str | None
    team: str | None

    def __post_init__(self) -> None:
        """Reject a skill in an unknown scope."""
        if self.scope not in _SCOPES:
            raise ValueError(f"'{self.scope}' is not a scope this system knows")


def applicable(
    skills: list[Skill], *, subject: str, teams: tuple[str, ...]
) -> tuple[Skill, ...]:
    """The skills `subject` can use, narrowest scope first."""
    chosen = [skill for skill in skills if _applies(skill, subject, teams)]

    chosen.sort(key=lambda skill: (_SCOPES.index(skill.scope), skill.name))
    return tuple(chosen)


def _applies(skill: Skill, subject: str, teams: tuple[str, ...]) -> bool:
    """Whether `skill` is in scope for this subject and their teams."""
    if skill.scope == "agent":
        return True
    if skill.scope == "team":
        return skill.team is not None and skill.team in teams
    return skill.owner is not None and skill.owner == subject
