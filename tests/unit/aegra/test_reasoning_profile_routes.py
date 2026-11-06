"""What the composer is told about ways of answering."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agent.aegra import reasoning_routes


async def _on(_request):
    return True


def _answer(config, *, offered=True):
    """The route's answer, with the per-user gate held open."""
    router = MagicMock()
    router.model_dump.return_value = config
    request = MagicMock()
    with (
        patch.object(reasoning_routes, "_routing_config", return_value=config),
        patch.object(reasoning_routes, "_offered_to", _on if offered else _off),
    ):
        import asyncio

        response = asyncio.run(reasoning_routes.list_reasoning_profiles(request))
    return json.loads(response.body)


async def _off(_request):
    return False


DIFFERENT = {
    "enabled": True,
    "tiers": [
        {"name": "fast", "model": "small"},
        {"name": "deep", "model": "large"},
    ],
    "profiles": [
        {"name": "fast", "tier": "fast", "effort": "low"},
        {"name": "accurate", "tier": "deep", "effort": "high"},
    ],
}

SAME = {
    "enabled": True,
    "tiers": [
        {"name": "fast", "model": "one"},
        {"name": "deep", "model": "one"},
    ],
    "profiles": [
        {"name": "fast", "tier": "fast", "effort": "low"},
        {"name": "accurate", "tier": "deep", "effort": "low"},
    ],
}


class TestWhatItReturns:
    def test_the_profiles_when_they_differ(self):
        said = _answer(DIFFERENT)
        assert [one["name"] for one in said["profiles"]] == ["fast", "accurate"]

    def test_nothing_when_they_would_not(self):
        assert _answer(SAME)["profiles"] == []

    def test_nothing_when_none_are_declared(self):
        assert _answer({"enabled": True, "tiers": []})["profiles"] == []


class TestWhatItWithholds:
    def test_the_model_does_not_travel(self):
        said = json.dumps(_answer(DIFFERENT))
        assert "small" not in said and "large" not in said

    def test_the_tier_does_not_travel_either(self):
        said = _answer(DIFFERENT)
        assert all("tier" not in one for one in said["profiles"])

    def test_only_the_name_and_its_effort_are_sent(self):
        said = _answer(DIFFERENT)
        assert all(set(one) == {"name", "effort"} for one in said["profiles"])


class TestItReadsTheRealConfiguration:
    """The accessor, unpatched."""

    def test_it_returns_the_shipped_configuration(self):
        found = reasoning_routes._routing_config()
        assert isinstance(found, dict)
        assert "tiers" in found, "the accessor did not reach the routing config"

    def test_the_shipped_profiles_are_visible_through_it(self):
        found = reasoning_routes._routing_config()
        assert [one.get("name") for one in found.get("profiles", [])] == [
            "fast",
            "balanced",
            "accurate",
        ]


class TestItNeverBreaksTheComposer:
    @pytest.mark.parametrize("broken", [None, "not a mapping", 7, {}])
    def test_a_configuration_it_cannot_read_yields_nothing(self, broken):
        assert _answer(broken)["profiles"] == []


class TestThePerUserGate:
    """`reasoning_profiles_enabled` is `scope: user` and defaults off."""

    DISTINCT = DIFFERENT

    def test_nothing_is_offered_when_the_person_has_not_turned_it_on(self):
        assert _answer(self.DISTINCT, offered=False)["profiles"] == []

    def test_and_the_choice_is_offered_when_they_have(self):
        assert _answer(self.DISTINCT, offered=True)["profiles"]

    def test_a_gate_that_cannot_be_resolved_reads_as_off(self):
        """The flag defaults off; an unreachable store is not a yes."""
        import asyncio

        request = MagicMock()
        with patch.object(
            reasoning_routes,
            "settled_for",
            side_effect=RuntimeError("no store"),
            create=True,
        ):
            assert asyncio.run(reasoning_routes._offered_to(request)) is False
