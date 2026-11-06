"""Handling a person's request about the data held on them."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.subject_request import Kind, Store, plan_request

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

STORES = (
    Store(name="threads", holds_data=True, on_legal_hold=False, deletable=True),
    Store(name="audit", holds_data=True, on_legal_hold=False, deletable=False),
    Store(name="memories", holds_data=True, on_legal_hold=True, deletable=True),
    Store(name="billing", holds_data=False, on_legal_hold=False, deletable=True),
)


def test_an_export_covers_every_store_holding_data():
    plan = plan_request(Kind.EXPORT, stores=STORES, now=NOW)
    assert plan.included == ("audit", "memories", "threads")


def test_an_export_skips_stores_holding_nothing():
    plan = plan_request(Kind.EXPORT, stores=STORES, now=NOW)
    assert "billing" not in plan.included


def test_an_export_is_not_blocked_by_a_legal_hold():
    plan = plan_request(Kind.EXPORT, stores=STORES, now=NOW)
    assert "memories" in plan.included


def test_a_deletion_leaves_out_what_cannot_be_deleted():
    plan = plan_request(Kind.DELETE, stores=STORES, now=NOW)
    assert "audit" not in plan.included


def test_a_deletion_leaves_out_what_is_under_hold():
    plan = plan_request(Kind.DELETE, stores=STORES, now=NOW)
    assert "memories" not in plan.included


def test_a_deletion_says_why_each_store_was_left_out():
    plan = plan_request(Kind.DELETE, stores=STORES, now=NOW)
    assert plan.withheld["memories"] == "under legal hold"


def test_a_store_that_keeps_records_by_law_says_so():
    plan = plan_request(Kind.DELETE, stores=STORES, now=NOW)
    assert plan.withheld["audit"] == "kept as a record"


def test_a_partial_deletion_is_reported_as_partial():
    assert plan_request(Kind.DELETE, stores=STORES, now=NOW).complete is False


def test_a_deletion_that_covers_everything_is_complete():
    simple = (
        Store(name="threads", holds_data=True, on_legal_hold=False, deletable=True),
    )
    assert plan_request(Kind.DELETE, stores=simple, now=NOW).complete is True


def test_the_person_is_told_what_will_remain():
    plan = plan_request(Kind.DELETE, stores=STORES, now=NOW)
    assert "audit" in plan.notice and "memories" in plan.notice


def test_a_complete_deletion_needs_no_such_notice():
    simple = (
        Store(name="threads", holds_data=True, on_legal_hold=False, deletable=True),
    )
    assert plan_request(Kind.DELETE, stores=simple, now=NOW).notice == ""


def test_a_deadline_is_set():
    plan = plan_request(Kind.EXPORT, stores=STORES, now=NOW)
    assert plan.due_at == NOW + timedelta(days=30)


def test_a_request_nothing_can_be_done_for_says_so():
    held = (
        Store(name="memories", holds_data=True, on_legal_hold=True, deletable=True),
    )
    plan = plan_request(Kind.DELETE, stores=held, now=NOW)
    assert plan.included == () and plan.complete is False


def test_a_request_against_stores_holding_nothing_finds_nothing():
    empty = (
        Store(name="billing", holds_data=False, on_legal_hold=False, deletable=True),
    )
    assert plan_request(Kind.EXPORT, stores=empty, now=NOW).included == ()


def test_a_request_with_no_stores_at_all_is_refused():
    with pytest.raises(ValueError):
        plan_request(Kind.EXPORT, stores=(), now=NOW)


def test_a_store_without_a_name_is_refused():
    with pytest.raises(ValueError):
        Store(name="  ", holds_data=True, on_legal_hold=False, deletable=True)
