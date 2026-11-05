"""Which capabilities are on, and who decided."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Scope(str, Enum):
    """Where a flag may be set. Widest first — the order is the rule."""

    DEPLOYMENT = "deployment"
    AGENT = "agent"
    USER = "user"


ORDER: tuple[Scope, ...] = (Scope.DEPLOYMENT, Scope.AGENT, Scope.USER)


class UnknownFeature(KeyError):
    """A flag nobody declared."""


@dataclass(frozen=True)
class Feature:
    """One declared capability."""

    scope: Scope
    default: bool = False
    ui_exposed: bool = False
    requires: tuple[str, ...] = ()
    cost: str = ""
    epic: str = ""


@dataclass(frozen=True)
class Settled:
    """The effective value, and enough to explain it."""

    name: str
    enabled: bool
    decided_by: str
    ui_exposed: bool
    overruled: bool = False
    missing: tuple[str, ...] = ()
    cost: str = ""


def _declared(name: str, registry: dict[str, Feature]) -> Feature:
    try:
        return registry[name]
    except KeyError as missing:
        raise UnknownFeature(name) from missing


def decide(
    name: str,
    *,
    registry: dict[str, Feature],
    deployment: bool | None = None,
    agent: bool | None = None,
    user: bool | None = None,
    others: dict[str, bool] | None = None,
) -> Settled:
    """Whether one flag is on, and which level settled it."""
    feature = _declared(name, registry)
    asked = {Scope.DEPLOYMENT: deployment, Scope.AGENT: agent, Scope.USER: user}

    enabled = feature.default
    decided_by = "default"
    overruled = False

    for scope in ORDER:
        wanted = asked.get(scope)
        if wanted is None:
            continue
        if ORDER.index(scope) > ORDER.index(feature.scope):
            if wanted and not enabled:
                overruled = True
            continue
        if wanted:
            if enabled or decided_by == "default":
                enabled = True
                decided_by = scope.value
            else:
                overruled = True
        else:
            enabled = False
            decided_by = scope.value

    missing = _unmet(feature, registry, others or {})
    if missing:
        enabled = False

    return Settled(
        name=name,
        enabled=enabled,
        decided_by=decided_by,
        ui_exposed=feature.ui_exposed,
        overruled=overruled,
        missing=missing,
        cost=feature.cost,
    )


def _unmet(
    feature: Feature, registry: dict[str, Feature], others: dict[str, bool]
) -> tuple[str, ...]:
    """Preconditions that are not satisfied."""
    unmet = []
    for required in feature.requires:
        _declared(required, registry)
        if not others.get(required, False):
            unmet.append(required)
    return tuple(unmet)


def effective(
    registry: dict[str, Feature],
    *,
    deployment: dict[str, bool] | None = None,
    agent: dict[str, bool] | None = None,
    user: dict[str, bool] | None = None,
) -> dict[str, Settled]:
    """Every flag, settled, with preconditions resolved first."""
    deployment, agent, user = deployment or {}, agent or {}, user or {}

    def pass_once(known: dict[str, bool]) -> dict[str, Settled]:
        return {
            name: decide(
                name,
                registry=registry,
                deployment=deployment.get(name),
                agent=agent.get(name),
                user=user.get(name),
                others=known,
            )
            for name in registry
        }

    first = pass_once({})
    return pass_once({name: s.enabled for name, s in first.items()})


def from_config(raw: Any) -> dict[str, Feature]:
    """Read the declared registry, refusing anything malformed."""
    if not isinstance(raw, dict):
        return {}

    registry: dict[str, Feature] = {}
    for name, declared in (raw.get("features") or {}).items():
        if not isinstance(declared, dict):
            raise ValueError(f"feature {name} is not a declaration")
        try:
            scope = Scope(declared.get("scope", ""))
        except ValueError as bad:
            raise ValueError(
                f"feature {name} declares an unknown scope {declared.get('scope')!r}"
            ) from bad
        registry[name] = Feature(
            scope=scope,
            default=bool(declared.get("default", False)),
            ui_exposed=bool(declared.get("ui_exposed", False)),
            requires=tuple(declared.get("requires") or ()),
            cost=str(declared.get("cost") or ""),
            epic=str(declared.get("epic") or ""),
        )
    return registry
