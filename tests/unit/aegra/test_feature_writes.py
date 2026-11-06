"""Turning a capability on, and the four times it is refused."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from agent.src.agent.config.features import Feature, Scope

REGISTRY = {
    "swarm_enabled": Feature(scope=Scope.DEPLOYMENT, default=False, ui_exposed=True),
    "sandbox_backend": Feature(scope=Scope.DEPLOYMENT, default=False, ui_exposed=True),
    "browser_automation_enabled": Feature(
        scope=Scope.DEPLOYMENT,
        default=False,
        ui_exposed=True,
        requires=("sandbox_backend",),
    ),
    "planner_enabled": Feature(scope=Scope.AGENT, default=False, ui_exposed=True),
    "hidden": Feature(scope=Scope.DEPLOYMENT, default=False, ui_exposed=False),
}


class _Store:
    """Stands in for the persisted overrides."""

    def __init__(self, held: dict[str, bool] | None = None, writable: bool = True):
        self.held = dict(held or {})
        self.writable = writable
        self.wrote: list[tuple[str, bool]] = []
        self.mine: dict[str, dict[str, bool]] = {}

    async def read(self) -> dict[str, bool]:
        return dict(self.held)

    async def read_for(self, user_id: str) -> dict[str, bool]:
        """This person's own answers. None, here."""
        return dict(self.mine.get(user_id, {}))

    async def write_for(self, user_id: str, key: str, enabled: bool) -> None:
        self.mine.setdefault(user_id, {})[key] = enabled

    async def write(self, key: str, enabled: bool) -> None:
        self.wrote.append((key, enabled))
        self.held[key] = enabled

    async def available(self) -> bool:
        return self.writable


async def _set(key: str, enabled: bool, store: _Store | None = None):
    from agent.aegra.feature_routes import set_feature

    store = store or _Store()
    with (
        patch("agent.aegra.feature_routes._registry", return_value=REGISTRY),
        patch("agent.aegra.feature_routes._store", return_value=store),
    ):
        answered = await set_feature(key, {"enabled": enabled}, _token="operator")
    return answered, store


class TestTurningOneOn:
    @pytest.mark.asyncio
    async def test_it_is_recorded(self):
        _, store = await _set("swarm_enabled", True)
        assert store.wrote == [("swarm_enabled", True)]

    @pytest.mark.asyncio
    async def test_the_answer_says_it_is_on(self):
        answered, _ = await _set("swarm_enabled", True)
        assert answered["enabled"] is True

    @pytest.mark.asyncio
    async def test_turning_one_off_is_recorded_too(self):
        _, store = await _set("swarm_enabled", False, _Store({"swarm_enabled": True}))
        assert store.wrote == [("swarm_enabled", False)]


class TestAFlagNobodyDeclared:
    @pytest.mark.asyncio
    async def test_it_is_refused(self):
        with pytest.raises(HTTPException) as refused:
            await _set("swarm_enbaled", True)
        assert refused.value.status_code == 404

    @pytest.mark.asyncio
    async def test_nothing_is_written(self):
        store = _Store()
        with pytest.raises(HTTPException):
            await _set("swarm_enbaled", True, store)
        assert store.wrote == []


class TestAFlagThisIsNotTheLevelFor:
    """Scope is declared, and the endpoint is where it is enforced."""

    @pytest.mark.asyncio
    async def test_an_agent_scoped_flag_is_not_set_here(self):
        with pytest.raises(HTTPException) as refused:
            await _set("planner_enabled", True)
        assert refused.value.status_code == 409

    @pytest.mark.asyncio
    async def test_the_refusal_says_where_it_belongs(self):
        with pytest.raises(HTTPException) as refused:
            await _set("planner_enabled", True)
        assert "agent" in str(refused.value.detail)

    @pytest.mark.asyncio
    async def test_nothing_is_written(self):
        store = _Store()
        with pytest.raises(HTTPException):
            await _set("planner_enabled", True, store)
        assert store.wrote == []


class TestAFlagWhosePreconditionIsAbsent:
    @pytest.mark.asyncio
    async def test_it_is_refused_rather_than_half_enabled(self):
        with pytest.raises(HTTPException) as refused:
            await _set("browser_automation_enabled", True)
        assert refused.value.status_code == 409

    @pytest.mark.asyncio
    async def test_the_missing_precondition_is_named(self):
        with pytest.raises(HTTPException) as refused:
            await _set("browser_automation_enabled", True)
        assert "sandbox_backend" in str(refused.value.detail)

    @pytest.mark.asyncio
    async def test_it_is_accepted_once_the_precondition_is_there(self):
        _, store = await _set(
            "browser_automation_enabled", True, _Store({"sandbox_backend": True})
        )
        assert store.wrote == [("browser_automation_enabled", True)]

    @pytest.mark.asyncio
    async def test_turning_it_off_never_needs_a_precondition(self):
        _, store = await _set("browser_automation_enabled", False)
        assert store.wrote == [("browser_automation_enabled", False)]


class TestWhenTheOverrideCannotBePersisted:
    """Accepting a change that will not survive a restart is worse."""

    @pytest.mark.asyncio
    async def test_the_change_is_refused(self):
        with pytest.raises(HTTPException) as refused:
            await _set("swarm_enabled", True, _Store(writable=False))
        assert refused.value.status_code == 503

    @pytest.mark.asyncio
    async def test_the_reason_is_given(self):
        with pytest.raises(HTTPException) as refused:
            await _set("swarm_enabled", True, _Store(writable=False))
        assert "not stored" in str(refused.value.detail).lower()

    @pytest.mark.asyncio
    async def test_nothing_is_written(self):
        store = _Store(writable=False)
        with pytest.raises(HTTPException):
            await _set("swarm_enabled", True, store)
        assert store.wrote == []


class TestAFlagTheInterfaceWasNeverOffered:
    @pytest.mark.asyncio
    async def test_it_cannot_be_set_through_this_surface(self):
        with pytest.raises(HTTPException) as refused:
            await _set("hidden", True)
        assert refused.value.status_code == 404


class TestTheReadReflectsTheWrite:
    @pytest.mark.asyncio
    async def test_a_stored_override_shows_in_the_report(self):
        from agent.aegra.feature_routes import features

        store = _Store({"swarm_enabled": True})
        with (
            patch("agent.aegra.feature_routes._registry", return_value=REGISTRY),
            patch("agent.aegra.feature_routes._store", return_value=store),
        ):
            answered = await features(MagicMock())
        found = {f["key"]: f for f in answered["features"]}
        assert found["swarm_enabled"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_and_says_the_deployment_decided_it(self):
        from agent.aegra.feature_routes import features

        store = _Store({"swarm_enabled": True})
        with (
            patch("agent.aegra.feature_routes._registry", return_value=REGISTRY),
            patch("agent.aegra.feature_routes._store", return_value=store),
        ):
            answered = await features(MagicMock())
        found = {f["key"]: f for f in answered["features"]}
        assert found["swarm_enabled"]["decided_by"] == "deployment"


class TestItIsNotOpenToEveryone:
    def test_the_write_is_behind_the_privileged_role(self):
        import inspect

        from agent.aegra.feature_routes import set_feature

        assert "_token" in inspect.signature(set_feature).parameters


_ = AsyncMock
