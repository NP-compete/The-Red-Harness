"""E33-T4 / MU-8. Two identities, one pending approval."""

from __future__ import annotations

import pytest

from agent.src.spaces.approval import (
    ApprovalNotYours,
    check_may_answer,
    may_answer,
)
from agent.src.spaces.store import ActiveRun

ALICE, BOB = "alice", "bob"
RUN = ActiveRun("r1", ALICE, "2026-10-30T00:00:00Z")


def test_the_person_who_triggered_it_may_answer():
    assert may_answer(RUN, actor=ALICE)
    check_may_answer(RUN, actor=ALICE, space_id="s1")


def test_another_member_may_not():
    assert not may_answer(RUN, actor=BOB)
    with pytest.raises(ApprovalNotYours):
        check_may_answer(RUN, actor=BOB, space_id="s1")


def test_the_refusal_says_whose_it_is_and_why():
    """A refusal that only says "forbidden" reads as a bug."""
    with pytest.raises(ApprovalNotYours) as exc:
        check_may_answer(RUN, actor=BOB, space_id="s1")
    message = str(exc.value)
    assert ALICE in message
    assert "their access, not yours" in message


def test_no_run_is_refused_rather_than_opened_up():
    """The one case where a fallback would become the rule."""
    assert not may_answer(None, actor=ALICE)
    with pytest.raises(ApprovalNotYours, match="cannot be identified"):
        check_may_answer(None, actor=ALICE, space_id="s1")


def test_two_blanks_are_not_a_match():
    """A missing identity on both sides would otherwise satisfy"""
    assert not may_answer(ActiveRun("r2", "", None), actor="")


def test_membership_is_not_the_question():
    """Being in the space is what lets Bob *see* it."""
    import inspect

    from agent.src.spaces import approval

    assert "is_member" not in inspect.getsource(approval)
