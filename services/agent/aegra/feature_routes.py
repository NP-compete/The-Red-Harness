"""The declared capabilities, as the interface sees them."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel

from agent._root import CONFIG_ROOT
from agent.aegra.auth_helpers import authenticated_user_id
from agent.aegra.eval_routes import _require_developer
from agent.src.agent.config.feature_overrides import overrides
from agent.src.agent.config.features import (
    Feature,
    Scope,
    effective,
    from_config,
)
from agent.src.agent.config.flag_audit import record_flag_change
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(tags=["features"])

REGISTRY_FILE = CONFIG_ROOT / "runtime" / "features.yaml"


def _registry() -> dict[str, Feature]:
    """The declared registry, or nothing if the file is not there."""
    import yaml

    if not REGISTRY_FILE.is_file():
        return {}
    return from_config(yaml.safe_load(REGISTRY_FILE.read_text()))


def _store() -> Any:
    """The feature override store."""
    return overrides()


async def _who(request: Request) -> str:
    """The caller, or nothing."""
    try:
        return await authenticated_user_id(request)
    except Exception:
        logger.debug("No caller identity for feature resolution", exc_info=True)
        return ""


def describe_features(
    *,
    registry: dict[str, Feature] | None = None,
    deployment: dict[str, bool] | None = None,
    agent: dict[str, bool] | None = None,
    user: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Every capability this surface is allowed to show."""
    declared = _registry() if registry is None else registry
    settled = effective(declared, deployment=deployment, agent=agent, user=user)

    return {
        "features": [
            {
                "key": name,
                "enabled": found.enabled,
                "scope": declared[name].scope.value,
                "decided_by": found.decided_by,
                "overruled": found.overruled,
                "missing": list(found.missing),
                "cost": found.cost,
            }
            for name, found in sorted(settled.items())
            if found.ui_exposed
        ],
        "unreadable": False,
    }


class FeatureOut(BaseModel):
    """One feature flag, its state, and what decided it."""

    key: str
    enabled: bool
    scope: str = ""
    decided_by: str = ""
    overruled: bool = False
    missing: list[str] = []
    cost: str = ""


class FeaturesOut(BaseModel):
    """Every feature flag the caller can see."""

    features: list[FeatureOut]
    unreadable: bool = False


class FeatureSetOut(BaseModel):
    """A feature flag after it was set."""

    key: str
    enabled: bool


class MyFeatureSetOut(BaseModel):
    """A feature flag after the caller set it for themselves."""

    key: str
    enabled: bool
    scope: str = "user"


@router.get("/features", responses={200: {"model": FeaturesOut}})
async def features(request: Request) -> dict[str, Any]:
    """Report the declared capabilities and their effective values."""
    try:
        declared = _registry()
    except Exception:
        logger.warning("Could not read the feature registry", exc_info=True)
        return {"features": [], "unreadable": True}

    store = _store()
    held = await store.read()
    mine = await store.read_for(await _who(request))
    return describe_features(registry=declared, deployment=held, user=mine)


@router.post("/features/{key}", responses={200: {"model": FeatureSetOut}})
async def set_feature(
    key: str,
    body: dict[str, Any] = Body(...),
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Turn one deployment-scoped capability on or off."""
    declared = _registry()
    feature = declared.get(key)

    if feature is None or not feature.ui_exposed:
        raise HTTPException(status_code=404, detail=f"No such capability: {key}")

    if feature.scope is not Scope.DEPLOYMENT:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{key} is set at the {feature.scope.value} level, not here. "
                "Accepting it would leave two places disagreeing with no way "
                "to tell which won."
            ),
        )

    enabled = bool(body.get("enabled"))
    store = _store()

    if not await store.available():
        raise HTTPException(
            status_code=503,
            detail=(
                "The change was not stored and so was not made. An override "
                "that cannot be persisted disappears at the next restart "
                "without anyone being told."
            ),
        )

    if enabled:
        held = await store.read()
        settled = effective({**declared}, deployment={**held, key: True})
        missing = settled[key].missing
        if missing:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{key} needs {', '.join(missing)} first. Enabling it now "
                    "would switch on a path that is only half there."
                ),
            )

    before = (await store.read()).get(key, feature.default)

    await store.write(key, enabled)

    record_flag_change(
        key=key,
        scope=feature.scope,
        was=bool(before),
        now=enabled,
        who=_token or "",
    )
    return {"key": key, "enabled": enabled}


@router.post("/me/features/{key}", responses={200: {"model": MyFeatureSetOut}})
async def set_my_feature(
    key: str,
    request: Request,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Turn one capability on or off for yourself."""
    declared = _registry()
    feature = declared.get(key)

    if feature is None or not feature.ui_exposed:
        raise HTTPException(status_code=404, detail=f"No such capability: {key}")

    if feature.scope is not Scope.USER:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{key} is set at the {feature.scope.value} level, not by a "
                "person. Accepting it here would leave two places "
                "disagreeing with no way to tell which won."
            ),
        )

    who = await _who(request)
    if not who:
        raise HTTPException(status_code=401, detail="Who is asking?")

    enabled = bool(body.get("enabled"))
    store = _store()
    if not await store.available():
        raise HTTPException(
            status_code=503,
            detail=(
                "The change was not stored and so was not made. A choice "
                "that cannot be persisted disappears at the next restart "
                "without anyone being told."
            ),
        )

    if enabled:
        settled = effective(
            {**declared},
            deployment=await store.read(),
            user={**await store.read_for(who), key: True},
        )[key]
        if not settled.enabled:
            if settled.missing:
                because = (
                    f"it needs {', '.join(settled.missing)}, which "
                    f"{'are' if len(settled.missing) > 1 else 'is'} not on"
                )
            elif settled.overruled:
                because = "a wider scope forbids it"
            else:
                because = f"the deployment decided it ({settled.decided_by})"
            raise HTTPException(
                status_code=409,
                detail=f"{key} cannot be turned on here: {because}.",
            )

    await store.write_for(who, key, enabled)
    return {"key": key, "enabled": enabled, "scope": "user"}


FLAG_REASONING_PROFILES = "reasoning_profiles_enabled"


async def settled_for(request: Request, key: str) -> bool:
    """Whether this capability is on for the caller."""
    declared = _registry()
    if key not in declared:
        return False
    store = _store()
    return effective(
        {**declared},
        deployment=await store.read(),
        user=await store.read_for(await _who(request)),
    )[key].enabled
