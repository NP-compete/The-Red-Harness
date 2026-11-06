"""Every authorisation decision leaves a record."""

from __future__ import annotations

from agent.src.security.journal import DecisionJournal, Entry
from agent.src.security.resolver import (
    Budget,
    Identity,
    Provenance,
    RefusalCode,
    RunContext,
    ToolCall,
    Trust,
    resolve,
)

CTX = RunContext(
    identity=Identity(subject="someone@example.com"),
    provenance=Provenance(config_fingerprint="cfg_7b19e4", schema_version=3),
)


class Authority:
    def __init__(self, held=True):
        self._held = held

    def holds(self, identity, call):
        return self._held


class Policy:
    def __init__(self, grade="allow"):
        self._grade = grade

    def decide(self, identity, call):
        return (self._grade, "medium", "")


class NoBudget:
    def remaining(self, ctx, call=None):
        return Budget()


def decide(journal, ctx=CTX, call=None, **over):
    sources = {"authority": Authority(), "policy": Policy(), "budget": NoBudget()}
    sources.update(over)
    return resolve(
        ctx, call or ToolCall(name="tracker.search"), journal=journal, **sources
    )


def test_an_allowed_call_is_recorded():
    journal = DecisionJournal()
    decide(journal)
    assert len(journal.entries) == 1
    assert journal.entries[0].outcome == "allowed"


def test_a_refusal_records_its_code():
    journal = DecisionJournal()
    decide(journal, authority=Authority(held=False))
    assert journal.entries[0].outcome == "refused"
    assert journal.entries[0].code is RefusalCode.NO_AUTHORITY


def test_an_approval_request_is_recorded_as_such():
    journal = DecisionJournal()
    decide(journal, policy=Policy(grade="ask"))
    assert journal.entries[0].outcome == "needs_approval"


def test_an_entry_names_the_identity_and_the_tool():
    journal = DecisionJournal()
    decide(journal, call=ToolCall(name="tracker.create_issue", server="tracker"))
    entry = journal.entries[0]
    assert entry.subject == "someone@example.com"
    assert entry.tool == "tracker.create_issue"


def test_an_entry_carries_the_provenance_of_the_run():
    journal = DecisionJournal()
    decide(journal)
    entry = journal.entries[0]
    assert entry.config_fingerprint == "cfg_7b19e4"
    assert entry.schema_version == 3
    assert entry.resolver_version


def test_an_entry_records_the_trust_level_that_applied():
    journal = DecisionJournal()
    decide(journal, ctx=CTX.with_untrusted_read())
    assert journal.entries[0].trust is Trust.UNTRUSTED_READ


def test_every_decision_produces_exactly_one_entry():
    journal = DecisionJournal()
    for _ in range(3):
        decide(journal)
    assert len(journal.entries) == 3


def test_resolving_without_a_journal_still_works():
    sources = {"authority": Authority(), "policy": Policy(), "budget": NoBudget()}
    assert resolve(CTX, ToolCall(name="x"), **sources)


def test_entries_are_read_only_once_recorded():
    journal = DecisionJournal()
    decide(journal)
    assert isinstance(journal.entries, tuple)
    assert isinstance(journal.entries[0], Entry)
