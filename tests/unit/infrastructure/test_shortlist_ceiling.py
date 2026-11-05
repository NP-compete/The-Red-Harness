"""The ceiling must not drop what the rules say must survive."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.src.infrastructure.shortlist import shortlist


def _tools(n, prefix="jira_t"):
    return [SimpleNamespace(name=f"{prefix}{i}", description="") for i in range(n)]


def _config(**kwargs):
    return SimpleNamespace(
        strategy=kwargs.pop("strategy", "static"),
        max_tools=kwargs.pop("max_tools", 2),
        always_include=kwargs.pop("always_include", []),
    )


def _offered(**kwargs):
    return [
        tool.name
        for tool in shortlist(
            kwargs.pop("tools", _tools(6)),
            _config(**kwargs.pop("config", {})),
            declared_servers=["jira_"],
            known_servers=["jira_"],
            keep=kwargs.pop("keep", ()),
        )
    ]


class TestTheCeilingYieldsToWhatMustSurvive:
    def test_every_already_called_tool_is_offered(self):
        keep = ["jira_t0", "jira_t1", "jira_t2", "jira_t3"]
        offered = _offered(keep=keep, config={"max_tools": 2})
        assert set(keep) <= set(offered)

    def test_the_list_runs_long_rather_than_losing_one(self):
        keep = ["jira_t0", "jira_t1", "jira_t2", "jira_t3"]
        assert len(_offered(keep=keep, config={"max_tools": 2})) >= len(keep)

    def test_nothing_unprotected_rides_along(self):
        keep = ["jira_t0", "jira_t1", "jira_t2", "jira_t3"]
        offered = _offered(keep=keep, config={"max_tools": 2})
        assert set(offered) == set(keep)

    def test_a_pinned_pattern_survives_too(self):
        offered = _offered(
            keep=(), config={"max_tools": 1, "always_include": ["jira_t4", "jira_t5"]}
        )
        assert {"jira_t4", "jira_t5"} <= set(offered)


class TestTheCeilingStillBites:
    def test_it_trims_when_nothing_is_protected(self):
        assert len(_offered(keep=(), config={"max_tools": 2})) == 2

    def test_it_keeps_the_order_they_arrived_in(self):
        assert _offered(keep=(), config={"max_tools": 2}) == ["jira_t0", "jira_t1"]

    def test_protected_tools_come_with_room_for_others(self):
        offered = _offered(keep=["jira_t5"], config={"max_tools": 3})
        assert "jira_t5" in offered and len(offered) == 3

    def test_no_ceiling_means_no_trimming(self):
        assert len(_offered(keep=(), config={"max_tools": 0})) == 6


class TestTheOtherStrategiesAreUnaffected:
    def test_doing_nothing_offers_everything(self):
        assert len(_offered(keep=(), config={"strategy": "none", "max_tools": 2})) == 6

    @pytest.mark.parametrize("strategy", ["static", "embedding"])
    def test_a_protected_tool_survives_whichever_is_chosen(self, strategy):
        keep = ["jira_t0", "jira_t1", "jira_t2"]
        offered = _offered(keep=keep, config={"strategy": strategy, "max_tools": 1})
        assert set(keep) <= set(offered)
