"""Getting back what someone had typed but not sent."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.agent.draft_recovery import Draft, Outcome, recover_draft

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def draft(**kwargs) -> Draft:
    defaults = {
        "thread": "t1",
        "text": "half a question about the numbers",
        "saved_at": NOW - timedelta(minutes=2),
        "attachments": (),
        "sent_at": None,
    }
    defaults.update(kwargs)
    return Draft(**defaults)


def test_a_recent_draft_is_offered_back():
    assert recover_draft(draft(), now=NOW).outcome is Outcome.OFFERED


def test_the_text_comes_back_as_it_was():
    assert recover_draft(draft(), now=NOW).text == "half a question about the numbers"


def test_a_draft_that_was_sent_is_not_offered_again():
    sent = draft(sent_at=NOW - timedelta(minutes=1))
    assert recover_draft(sent, now=NOW).outcome is Outcome.ALREADY_SENT


def test_a_sent_draft_comes_back_empty():
    sent = draft(sent_at=NOW - timedelta(minutes=1))
    assert recover_draft(sent, now=NOW).text == ""


def test_an_empty_draft_is_not_worth_offering():
    assert (
        recover_draft(draft(text="   "), now=NOW).outcome is Outcome.NOTHING_TO_RECOVER
    )


def test_a_draft_that_is_only_attachments_is_still_worth_offering():
    assert (
        recover_draft(draft(text="", attachments=("report.pdf",)), now=NOW).outcome
        is Outcome.OFFERED
    )


def test_the_attachments_come_back_too():
    recovered = recover_draft(draft(attachments=("report.pdf",)), now=NOW)
    assert recovered.attachments == ("report.pdf",)


def test_an_old_draft_is_not_offered():
    stale = draft(saved_at=NOW - timedelta(days=14))
    assert recover_draft(stale, now=NOW).outcome is Outcome.TOO_OLD


def test_how_old_a_draft_is_is_reported():
    older = draft(saved_at=NOW - timedelta(hours=3))
    assert recover_draft(older, now=NOW).age == timedelta(hours=3)


def test_a_draft_is_offered_with_its_age_in_words():
    older = draft(saved_at=NOW - timedelta(hours=3))
    assert "3 hours" in recover_draft(older, now=NOW).reason


def test_a_draft_saved_in_the_future_is_treated_as_just_saved():
    odd = draft(saved_at=NOW + timedelta(minutes=5))
    assert recover_draft(odd, now=NOW).age == timedelta(0)


def test_how_long_the_draft_may_still_be_kept_is_reported():
    recovered = recover_draft(draft(), now=NOW)
    assert recovered.expires_at == draft().saved_at + timedelta(days=7)


def test_a_draft_for_a_thread_that_is_gone_is_not_offered():
    assert (
        recover_draft(draft(), now=NOW, thread_exists=False).outcome
        is Outcome.THREAD_GONE
    )


def test_a_draft_for_a_missing_thread_still_says_what_was_typed():
    recovered = recover_draft(draft(), now=NOW, thread_exists=False)
    assert recovered.text == "half a question about the numbers"


def test_a_draft_with_no_thread_is_refused():
    with pytest.raises(ValueError):
        draft(thread="  ")


def test_a_draft_sent_before_it_was_written_is_refused():
    with pytest.raises(ValueError):
        draft(saved_at=NOW, sent_at=NOW - timedelta(minutes=5))
