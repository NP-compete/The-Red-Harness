"""The `user` scope has somewhere to live (CFG-1, CFG-8)."""

from __future__ import annotations

import pytest

from agent.src.agent.config.feature_overrides import FeatureOverrides, user_key
from agent.src.agent.config.features import Feature, Scope, effective


class FakeRedis:
    """Enough of the client to hold hashes."""

    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    async def hset(self, key: str, field: str, value: str) -> None:
        self.hashes.setdefault(key, {})[field] = value


@pytest.fixture
def store():
    client = FakeRedis()
    return FeatureOverrides(client_factory=lambda: client), client


REGISTRY = {
    "a_user_flag": Feature(
        scope=Scope.USER,
        default=False,
        ui_exposed=True,
        requires=(),
        cost="",
        epic="E17",
    ),
}


class TestEachPersonHasTheirOwn:
    @pytest.mark.asyncio
    async def test_a_choice_is_read_back(self, store):
        overrides, _ = store
        await overrides.write_for("ada", "a_user_flag", True)
        assert await overrides.read_for("ada") == {"a_user_flag": True}

    @pytest.mark.asyncio
    async def test_and_not_by_anybody_else(self, store):
        overrides, _ = store
        await overrides.write_for("ada", "a_user_flag", True)
        assert await overrides.read_for("grace") == {}

    @pytest.mark.asyncio
    async def test_it_does_not_touch_the_deployment_hash(self, store):
        overrides, client = store
        await overrides.write_for("ada", "a_user_flag", True)
        assert await overrides.read() == {}
        assert user_key("ada") in client.hashes

    @pytest.mark.asyncio
    async def test_nobody_in_particular_reads_nothing(self, store):
        overrides, _ = store
        assert await overrides.read_for("") == {}

    @pytest.mark.asyncio
    async def test_saying_no_is_recorded(self, store):
        """Absent and false are different answers."""
        overrides, _ = store
        await overrides.write_for("ada", "a_user_flag", False)
        assert await overrides.read_for("ada") == {"a_user_flag": False}


class TestAPersonCannotStepAroundAWiderNo:
    def test_the_users_yes_is_settled_against_the_deployment(self):
        registry = {
            "a_user_flag": Feature(
                scope=Scope.USER,
                default=False,
                ui_exposed=True,
                requires=("a_precondition",),
                cost="",
                epic="E17",
            ),
            "a_precondition": Feature(
                scope=Scope.DEPLOYMENT,
                default=False,
                ui_exposed=True,
                requires=(),
                cost="",
                epic="E21",
            ),
        }
        settled = effective(registry, user={"a_user_flag": True})
        assert settled["a_user_flag"].enabled is False, (
            "a person turned on a capability whose precondition the "
            "deployment has not provided"
        )

    def test_and_their_yes_holds_when_nothing_forbids_it(self):
        settled = effective(REGISTRY, user={"a_user_flag": True})
        assert settled["a_user_flag"].enabled is True
