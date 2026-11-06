"""Small structured values an agent produces, kept per person or per team."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Owner:
    """Who an artifact belongs to, and the teams they can store under."""

    subject: str
    teams: tuple[str, ...] = ()


class ArtifactStore:
    """Key-value artifacts per owner and team, under size quotas."""

    def __init__(self, *, max_bytes_per_owner: int, max_bytes_per_value: int) -> None:
        """Start empty, with per-owner and per-value size caps."""
        self._max_total = max_bytes_per_owner
        self._max_value = max_bytes_per_value
        self._values: dict[tuple[str, str], str] = {}

    def put(
        self, owner: Owner, *, key: str, value: str, team: str | None = None
    ) -> None:
        """Store `value` under `key`, for the owner or one of their teams."""
        if team is not None and team not in owner.teams:
            raise PermissionError(f"{owner.subject} is not in {team}")

        size = len(value.encode())
        if size > self._max_value:
            raise ValueError(f"'{key}' is larger than a single artifact may be")

        scope = team or owner.subject
        slot = (scope, key)
        projected = self._used(scope) - len(self._values.get(slot, "").encode()) + size
        if projected > self._max_total:
            raise ValueError(f"{scope} has no room left for '{key}'")

        self._values[slot] = value

    def get(self, owner: Owner, *, key: str, team: str | None = None) -> str | None:
        """The value under `key`, or `None` if it is absent or out of scope."""
        if team is not None:
            return self._values.get((team, key)) if team in owner.teams else None
        return self._values.get((owner.subject, key))

    def delete(self, owner: Owner, *, key: str, team: str | None = None) -> None:
        """Remove `key` from the owner's scope or one of their teams."""
        scope = team or owner.subject
        if team is not None and team not in owner.teams:
            raise PermissionError(f"{owner.subject} is not in {team}")
        self._values.pop((scope, key), None)

    def keys(self, owner: Owner) -> list[str]:
        """Every key the owner can see, their own and their teams'."""
        visible = {owner.subject, *owner.teams}
        return [key for (scope, key) in self._values if scope in visible]

    def usage(self, owner: Owner) -> int:
        """How many bytes the owner's own artifacts take up."""
        return self._used(owner.subject)

    def _used(self, scope: str) -> int:
        """How many bytes the artifacts in `scope` take up."""
        return sum(
            len(value.encode()) for (s, _), value in self._values.items() if s == scope
        )


_SESSION_ARTIFACTS: ArtifactStore | None = None


def session_artifacts() -> ArtifactStore:
    """The store this process keeps artifacts in."""
    global _SESSION_ARTIFACTS
    if _SESSION_ARTIFACTS is None:
        from agent.src.agent.config import agent_config

        config = agent_config.get_knowledge_config()
        _SESSION_ARTIFACTS = ArtifactStore(
            max_bytes_per_owner=config.artifact_max_bytes,
            max_bytes_per_value=config.artifact_value_max_bytes,
        )
    return _SESSION_ARTIFACTS
