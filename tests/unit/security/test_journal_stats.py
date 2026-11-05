"""How often a run stopped to ask, which is the number that decides if asking still works."""

from __future__ import annotations

from agent.src.security.journal import DecisionJournal, Entry, summarise
from agent.src.security.resolver import RefusalCode, Trust


def entry(outcome="allowed", code=None, trust=Trust.CLEAN, tool="t") -> Entry:
    return Entry(
        subject="someone@example.com",
        tool=tool,
        outcome=outcome,
        trust=trust,
        config_fingerprint="cfg",
        schema_version=3,
        resolver_version="1",
        code=code,
    )


def journal(*entries: Entry) -> DecisionJournal:
    j = DecisionJournal()
    for e in entries:
        j.record(e)
    return j


def test_an_empty_run_asked_nothing():
    stats = summarise(journal())
    assert stats.total == 0
    assert stats.asked == 0
    assert stats.ask_rate == 0.0


def test_it_counts_each_outcome():
    stats = summarise(
        journal(
            entry(outcome="allowed"),
            entry(outcome="needs_approval"),
            entry(outcome="refused", code=RefusalCode.POLICY_DENIED),
            entry(outcome="unavailable"),
        )
    )
    assert (stats.allowed, stats.asked, stats.refused, stats.unavailable) == (
        1,
        1,
        1,
        1,
    )


def test_the_ask_rate_is_the_share_of_calls_that_stopped():
    stats = summarise(journal(entry(), entry(), entry(outcome="needs_approval")))
    assert stats.ask_rate == 1 / 3


def test_refusals_are_broken_down_by_cause():
    stats = summarise(
        journal(
            entry(outcome="refused", code=RefusalCode.NO_AUTHORITY),
            entry(outcome="refused", code=RefusalCode.NO_AUTHORITY),
            entry(outcome="refused", code=RefusalCode.BUDGET_EXHAUSTED),
        )
    )
    assert stats.refusals_by_code[RefusalCode.NO_AUTHORITY] == 2
    assert stats.refusals_by_code[RefusalCode.BUDGET_EXHAUSTED] == 1


def test_it_names_the_tools_people_were_asked_about_most():
    stats = summarise(
        journal(
            entry(outcome="needs_approval", tool="tracker.create_issue"),
            entry(outcome="needs_approval", tool="tracker.create_issue"),
            entry(outcome="needs_approval", tool="mail.send"),
        )
    )
    assert stats.asked_most == ("tracker.create_issue", 2)


def test_nothing_is_named_when_nothing_was_asked():
    assert summarise(journal(entry())).asked_most is None


def test_it_reports_whether_the_run_ever_read_untrusted_content():
    assert summarise(journal(entry(trust=Trust.UNTRUSTED_READ))).ever_untrusted is True
    assert summarise(journal(entry())).ever_untrusted is False
