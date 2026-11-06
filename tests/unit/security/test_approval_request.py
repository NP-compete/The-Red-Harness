"""The life of a request that is waiting for a human."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.approval_request import (
    ApprovalRequest,
    Outcome,
    settle,
)

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def request(**kwargs) -> ApprovalRequest:
    defaults = {
        "tool": "deploy",
        "requested_by": "ana",
        "requested_at": NOW - timedelta(minutes=5),
        "expires_at": NOW + timedelta(minutes=25),
        "eligible_approvers": ("bo", "cy"),
        "self_approval_allowed": False,
    }
    defaults.update(kwargs)
    return ApprovalRequest(**defaults)


def test_an_eligible_approver_can_approve():
    assert (
        settle(request(), approver="bo", approved=True, now=NOW).outcome
        is Outcome.APPROVED
    )


def test_an_eligible_approver_can_deny():
    assert (
        settle(request(), approver="bo", approved=False, now=NOW).outcome
        is Outcome.DENIED
    )


def test_someone_who_was_not_asked_cannot_approve():
    settled = settle(request(), approver="dee", approved=True, now=NOW)
    assert settled.outcome is Outcome.REFUSED


def test_an_ineligible_approver_is_told_why():
    settled = settle(request(), approver="dee", approved=True, now=NOW)
    assert "not one of the approvers" in settled.reason


def test_the_requester_cannot_approve_their_own_request():
    settled = settle(request(), approver="ana", approved=True, now=NOW)
    assert settled.outcome is Outcome.REFUSED


def test_self_approval_is_named_as_the_reason():
    settled = settle(request(), approver="ana", approved=True, now=NOW)
    assert "own request" in settled.reason


def test_self_approval_is_possible_when_it_was_deliberately_allowed():
    allowed = request(self_approval_allowed=True, eligible_approvers=("ana",))
    assert (
        settle(allowed, approver="ana", approved=True, now=NOW).outcome
        is Outcome.APPROVED
    )


def test_the_requester_may_always_withdraw_their_own_request():
    settled = settle(request(), approver="ana", approved=False, now=NOW)
    assert settled.outcome is Outcome.DENIED


def test_an_expired_request_cannot_be_approved():
    late = NOW + timedelta(hours=1)
    assert (
        settle(request(), approver="bo", approved=True, now=late).outcome
        is Outcome.EXPIRED
    )


def test_an_expired_request_says_how_long_it_waited():
    late = NOW + timedelta(hours=1)
    assert (
        "30 minutes" in settle(request(), approver="bo", approved=True, now=late).reason
    )


def test_an_expiry_is_a_refusal_not_a_silent_go_ahead():
    late = NOW + timedelta(hours=1)
    assert settle(request(), approver="bo", approved=True, now=late).permitted is False


def test_an_approval_permits_the_call():
    assert settle(request(), approver="bo", approved=True, now=NOW).permitted is True


def test_a_denial_does_not_permit_the_call():
    assert settle(request(), approver="bo", approved=False, now=NOW).permitted is False


def test_the_decision_records_who_made_it():
    assert settle(request(), approver="bo", approved=True, now=NOW).decided_by == "bo"


def test_the_decision_records_how_long_the_person_took():
    settled = settle(request(), approver="bo", approved=True, now=NOW)
    assert settled.waited_seconds == 300.0


def test_a_request_with_no_eligible_approvers_is_refused():
    orphan = request(eligible_approvers=())
    assert (
        settle(orphan, approver="bo", approved=True, now=NOW).outcome is Outcome.REFUSED
    )


def test_a_request_with_no_approvers_says_nobody_can_act_on_it():
    orphan = request(eligible_approvers=())
    assert "nobody" in settle(orphan, approver="bo", approved=True, now=NOW).reason


@pytest.mark.parametrize("field", ["tool", "requested_by"])
def test_an_anonymous_request_is_refused(field):
    with pytest.raises(ValueError):
        request(**{field: "  "})


def test_a_request_that_expires_before_it_is_made_is_refused():
    with pytest.raises(ValueError):
        request(expires_at=NOW - timedelta(hours=1))
