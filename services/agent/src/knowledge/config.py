"""Which scopes a deployment keeps, and how retrieval is tuned."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.src.knowledge.scopes import Scope

KEPT = (Scope.SESSION, Scope.USER, Scope.TEAM, Scope.AGENT)

DEFAULT_ORDER = (Scope.SESSION, Scope.USER, Scope.TEAM, Scope.AGENT)


class KnowledgeMisconfigured(ValueError):
    """A setting that would make the library quietly answer nothing."""


@dataclass(frozen=True)
class Knowledge:
    """The knowledge settings read from the config tree."""

    enabled: bool = False
    scopes: tuple[Scope, ...] = ()
    teams: tuple[str, ...] = ()
    order: tuple[Scope, ...] = ()
    top_k: int = 8
    min_score: float = 0.35
    chunk_size: int = 1200
    chunk_overlap: int = 200
    user_max_bytes: int = 209_715_200
    agent_max_bytes: int = 1_073_741_824
    artifact_max_bytes: int = 65_536
    artifact_value_max_bytes: int = 8_192


def _scope(name: str, *, where: str) -> Scope:
    """`name` as a scope, or raise naming the scopes there are."""
    try:
        found = Scope(name)
    except ValueError:
        raise KnowledgeMisconfigured(
            f"{name!r} in knowledge.{where} is not a scope; "
            f"the scopes are {', '.join(s.value for s in KEPT)}"
        ) from None
    if found not in KEPT:
        raise KnowledgeMisconfigured(
            f"{name!r} in knowledge.{where} is not a scope this library keeps"
        )
    return found


def read_knowledge(raw: Any) -> Knowledge:
    """Read the `knowledge` section, falling back to defaults."""
    section = (raw or {}).get("knowledge") if isinstance(raw, dict) else None
    if not isinstance(section, dict):
        return Knowledge()

    switch = section.get("enabled", False)
    if not isinstance(switch, bool):
        raise KnowledgeMisconfigured(
            f"knowledge.enabled must be true or false, not {switch!r}. A "
            "quoted 'false' is a string, and a non-empty string would turn "
            "this on."
        )
    if not switch:
        return Knowledge()

    declared = section.get("scopes") or {}
    if not isinstance(declared, dict):
        raise KnowledgeMisconfigured("knowledge.scopes must name each scope")
    for name in declared:
        _scope(str(name), where="scopes")

    kept = tuple(scope for scope in KEPT if declared.get(scope.value, True))
    if not kept:
        return Knowledge()

    retrieval = section.get("retrieval") or {}
    asked = retrieval.get("default_order")
    order = (
        tuple(_scope(str(name), where="retrieval.default_order") for name in asked)
        if asked
        else DEFAULT_ORDER
    )
    order = tuple(scope for scope in order if scope in kept)

    limits = section.get("limits") or {}

    artifact_total = _at_least(limits, "artifact_max_bytes", default=65_536, floor=0)
    artifact_value = _at_least(
        limits, "artifact_value_max_bytes", default=8_192, floor=0
    )
    if artifact_value > artifact_total:
        if limits.get("artifact_value_max_bytes") is not None:
            raise KnowledgeMisconfigured(
                f"knowledge.artifact_value_max_bytes is {artifact_value}, above "
                f"the whole allowance of {artifact_total}, so nothing could "
                "ever be kept"
            )
        artifact_value = artifact_total

    chunk_size = _at_least(retrieval, "chunk_size", default=1200, floor=1)
    chunk_overlap = _at_least(retrieval, "chunk_overlap", default=200, floor=0)
    if chunk_overlap >= chunk_size:
        raise KnowledgeMisconfigured(
            f"knowledge.retrieval.chunk_overlap is {chunk_overlap}, which is not "
            f"less than chunk_size {chunk_size}; a chunk that never advances "
            f"makes the corpus unusable"
        )

    return Knowledge(
        enabled=True,
        scopes=kept,
        teams=_teams(section),
        order=order,
        top_k=_at_least(retrieval, "top_k", default=8, floor=1),
        min_score=_fraction(retrieval, "min_score", default=0.35),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        user_max_bytes=_at_least(
            limits, "user_max_bytes", default=209_715_200, floor=0
        ),
        agent_max_bytes=_at_least(
            limits, "agent_max_bytes", default=1_073_741_824, floor=0
        ),
        artifact_max_bytes=artifact_total,
        artifact_value_max_bytes=artifact_value,
    )


def _teams(section: dict) -> tuple[str, ...]:
    """The groups a team corpus may belong to."""
    raw = section.get("teams")
    if raw is None:
        return ()
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
        raise KnowledgeMisconfigured(
            f"knowledge.teams is a list of directory groups, not {type(raw).__name__}"
        )
    found = tuple(str(name).strip() for name in raw if str(name).strip())
    if len(found) != len(set(found)):
        raise KnowledgeMisconfigured("knowledge.teams names the same group twice")
    return found


def _at_least(section: dict, field: str, *, default: int, floor: int) -> int:
    """`field` as a whole number no lower than `floor`."""
    raw = section.get(field)
    if raw is None:
        return default
    try:
        found = int(raw)
    except (TypeError, ValueError):
        raise KnowledgeMisconfigured(
            f"knowledge.{field} must be a whole number, not {raw!r}"
        ) from None
    if found < floor:
        raise KnowledgeMisconfigured(
            f"knowledge.{field} is {found}; below {floor} it answers nothing "
            f"while looking configured"
        )
    return found


def _fraction(section: dict, field: str, *, default: float) -> float:
    """`field` as a fraction, or `default` if it is missing or bad."""
    raw = section.get(field)
    if raw is None:
        return default
    try:
        found = float(raw)
    except (TypeError, ValueError):
        raise KnowledgeMisconfigured(
            f"knowledge.{field} must be a number, not {raw!r}"
        ) from None
    if not 0.0 <= found <= 1.0:
        raise KnowledgeMisconfigured(
            f"knowledge.{field} is {found}; a score sits between 0 and 1"
        )
    return found
