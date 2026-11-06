"""Sending the model the tools a turn could plausibly need."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from agent.src.agent.config.middleware import ToolShortlistConfig
from agent.src.infrastructure.shortlist import shortlist


@dataclass
class _Tool:
    name: str


def tools(*names: str) -> list[_Tool]:
    return [_Tool(name) for name in names]


def names(found) -> list[str]:
    return [t.name for t in found]


class TestTheDefaultChangesNothing:
    def test_everything_is_sent_when_no_strategy_is_chosen(self):
        every = tools("read_file", "grep", "atlan_search", "gitlab_mr")
        assert names(shortlist(every, ToolShortlistConfig())) == names(every)

    def test_the_shipped_default_is_to_send_everything(self):
        assert ToolShortlistConfig().strategy == "none"

    def test_a_strategy_nobody_implements_is_refused(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ToolShortlistConfig(strategy="telepathy")


class TestTheStaticStrategy:
    def test_only_the_servers_this_agent_declared_are_sent(self):
        found = shortlist(
            tools("atlan_search", "gitlab_mr", "read_file"),
            ToolShortlistConfig(strategy="static"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "atlan_search" not in names(found)

    def test_a_declared_server_keeps_its_tools(self):
        found = shortlist(
            tools("atlan_search", "gitlab_mr"),
            ToolShortlistConfig(strategy="static"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "gitlab_mr" in names(found)

    def test_a_tool_that_belongs_to_no_server_is_kept(self):
        found = shortlist(
            tools("read_file", "atlan_search"),
            ToolShortlistConfig(strategy="static"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "read_file" in names(found)

    def test_a_server_whose_name_merely_starts_the_same_is_not_declared(self):
        found = shortlist(
            tools(
                "atlantis_deploy",
            ),
            ToolShortlistConfig(strategy="static"),
            declared_servers=("atlan",),
            known_servers=("atlan", "atlantis"),
        )
        assert names(found) == []


class TestTheTwoRulesNothingMayBreak:
    def test_a_tool_already_called_in_this_run_is_never_dropped(self):
        found = shortlist(
            tools("atlan_search", "gitlab_mr"),
            ToolShortlistConfig(strategy="static"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
            keep=("atlan_search",),
        )
        assert "atlan_search" in names(found)

    def test_an_unconnected_server_keeps_its_placeholder(self):
        found = shortlist(
            tools(
                "miro_board",
            ),
            ToolShortlistConfig(strategy="static"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "miro"),
            keep=("miro_board",),
        )
        assert names(found) == ["miro_board"]

    def test_what_must_be_kept_survives_the_ceiling_too(self):
        found = shortlist(
            tools(*[f"t{i}" for i in range(10)]),
            ToolShortlistConfig(strategy="static", max_tools=2),
            declared_servers=(),
            keep=("t9",),
        )
        assert "t9" in names(found)


class TestAlwaysInclude:
    def test_a_named_tool_is_always_sent(self):
        found = shortlist(
            tools("atlan_search", "gitlab_mr"),
            ToolShortlistConfig(strategy="static", always_include=["atlan_search"]),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "atlan_search" in names(found)

    def test_a_glob_keeps_a_family_of_tools(self):
        found = shortlist(
            tools("mcp_read_resource", "mcp_list_resources", "atlan_search"),
            ToolShortlistConfig(strategy="static", always_include=["mcp_*"]),
            declared_servers=(),
        )
        assert set(names(found)) >= {"mcp_read_resource", "mcp_list_resources"}


class TestTheCeiling:
    def test_a_long_list_is_cut_to_the_ceiling(self):
        found = shortlist(
            tools(*[f"t{i}" for i in range(50)]),
            ToolShortlistConfig(strategy="static", max_tools=5),
            declared_servers=(),
        )
        assert len(found) == 5

    def test_the_order_the_tools_arrived_in_is_kept(self):
        found = shortlist(
            tools("b_one", "a_two", "c_three"),
            ToolShortlistConfig(strategy="static", max_tools=3),
            declared_servers=("b", "a", "c"),
        )
        assert names(found) == ["b_one", "a_two", "c_three"]

    def test_no_ceiling_means_no_cut(self):
        every = tools(*[f"t{i}" for i in range(50)])
        found = shortlist(
            every,
            ToolShortlistConfig(strategy="static", max_tools=0),
            declared_servers=(),
        )
        assert len(found) == 50


class TestAServersNameIsNotItsToolPrefix:
    """`unstructured-data` names its tools `unstructured_*`."""

    def test_a_declared_prefix_is_used_in_place_of_the_name(self):
        from agent.src.infrastructure.shortlist import tool_prefixes

        servers = {"unstructured-data": {"tool_prefix": "unstructured"}}
        assert tool_prefixes(["unstructured-data"], servers) == ["unstructured"]

    def test_a_server_that_declares_none_falls_back_to_its_name(self):
        from agent.src.infrastructure.shortlist import tool_prefixes

        assert tool_prefixes(["gitlab"], {"gitlab": {}}) == ["gitlab"]

    def test_a_server_nobody_configured_falls_back_to_its_name(self):
        from agent.src.infrastructure.shortlist import tool_prefixes

        assert tool_prefixes(["mystery"], {}) == ["mystery"]

    def test_an_empty_prefix_is_not_taken_literally(self):
        from agent.src.infrastructure.shortlist import tool_prefixes

        assert tool_prefixes(["gitlab"], {"gitlab": {"tool_prefix": ""}}) == ["gitlab"]

    def test_the_prefix_is_what_the_matching_then_uses(self):
        found = shortlist(
            tools("unstructured_parse", "atlan_search"),
            ToolShortlistConfig(strategy="static"),
            declared_servers=("unstructured",),
            known_servers=("unstructured", "atlan"),
        )
        assert names(found) == ["unstructured_parse"]


class TestAStrategyThatIsNotBuiltYet:
    """`embedding` is a value the config accepts and nothing serves."""

    def test_it_narrows_rather_than_sending_everything(self):
        found = shortlist(
            tools("gitlab_mr", "atlan_search"),
            ToolShortlistConfig(strategy="embedding"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "atlan_search" not in names(found)

    def test_it_keeps_what_the_declared_servers_offer(self):
        found = shortlist(
            tools("gitlab_mr", "atlan_search"),
            ToolShortlistConfig(strategy="embedding"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
        )
        assert "gitlab_mr" in names(found)

    def test_the_two_rules_still_hold(self):
        found = shortlist(
            tools("gitlab_mr", "atlan_search"),
            ToolShortlistConfig(strategy="embedding"),
            declared_servers=("gitlab",),
            known_servers=("gitlab", "atlan"),
            keep=("atlan_search",),
        )
        assert "atlan_search" in names(found)

    def test_asking_for_it_is_reported(self, caplog):
        import logging

        from agent.src.infrastructure import shortlist as module

        module._told_about_embedding = False
        with caplog.at_level(logging.WARNING):
            shortlist(
                tools("gitlab_mr"),
                ToolShortlistConfig(strategy="embedding"),
                declared_servers=("gitlab",),
                known_servers=("gitlab",),
            )
        assert "embedding" in caplog.text.lower()

    def test_it_is_not_repeated_on_every_call(self, caplog):
        import logging

        from agent.src.infrastructure import shortlist as module

        module._told_about_embedding = False
        config = ToolShortlistConfig(strategy="embedding")
        with caplog.at_level(logging.WARNING):
            for _ in range(3):
                shortlist(tools("gitlab_mr"), config, declared_servers=("gitlab",))
        assert caplog.text.lower().count("not built yet") == 1
