"""Tracking whether a run has read content from an untrusted source."""

from __future__ import annotations

import pytest

from agent.src.security.resolver import RunContext, Trust
from agent.src.security.trust import RunTrust, ToolResult


def result(server: str | None = "tracker", **kwargs) -> ToolResult:
    kwargs.setdefault("tool_name", "search")
    return ToolResult(server=server, **kwargs)


def test_a_run_starts_clean():
    assert RunTrust(trusted_servers=["docs"]).level is Trust.CLEAN


def test_reading_from_an_untrusted_server_taints_the_run():
    trust = RunTrust(trusted_servers=["docs"])
    trust.record(result(server="tracker"))
    assert trust.level is Trust.UNTRUSTED_READ


def test_reading_from_a_trusted_server_leaves_the_run_clean():
    trust = RunTrust(trusted_servers=["docs"])
    trust.record(result(server="docs"))
    assert trust.level is Trust.CLEAN


def test_a_local_tool_result_is_trusted():
    trust = RunTrust(trusted_servers=["docs"])
    trust.record(result(server=None))
    assert trust.level is Trust.CLEAN


def test_no_trusted_servers_means_every_server_is_untrusted():
    trust = RunTrust(trusted_servers=[])
    trust.record(result(server="docs"))
    assert trust.level is Trust.UNTRUSTED_READ


def test_taint_survives_later_trusted_reads():
    trust = RunTrust(trusted_servers=["docs"])
    trust.record(result(server="tracker"))
    trust.record(result(server="docs"))
    assert trust.level is Trust.UNTRUSTED_READ


def test_there_is_no_way_to_clear_taint():
    trust = RunTrust(trusted_servers=["docs"])
    trust.record(result(server="tracker"))
    assert not any(name.startswith(("clear", "reset")) for name in dir(trust))
    with pytest.raises(AttributeError):
        trust.level = Trust.CLEAN


def test_it_remembers_which_sources_tainted_the_run():
    trust = RunTrust(trusted_servers=["docs"])
    trust.record(result(server="tracker", tool_name="search_incidents"))
    trust.record(result(server="mail", tool_name="list"))
    assert trust.sources == ("tracker.search_incidents", "mail.list")


def test_applying_to_a_context_escalates_it():
    trust = RunTrust(trusted_servers=["docs"])
    trust.record(result(server="tracker"))
    assert trust.apply(RunContext(identity=None)).trust is Trust.UNTRUSTED_READ


def test_applying_a_clean_run_leaves_the_context_untouched():
    ctx = RunContext(identity=None)
    assert RunTrust(trusted_servers=["docs"]).apply(ctx) is ctx
