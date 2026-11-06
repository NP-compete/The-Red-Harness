"""Showing what a run would do, without doing it."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.agent.dry_run import Intent, preview


def intent(**kwargs) -> Intent:
    defaults = {
        "tool": "write-file",
        "target": "out/report.md",
        "writes": True,
        "reversible": True,
        "needs_approval": False,
        "estimated_cost": Decimal("0.10"),
    }
    defaults.update(kwargs)
    return Intent(**defaults)


def test_a_preview_changes_nothing():
    assert preview([intent()]).executed is False


def test_a_preview_lists_what_would_happen():
    result = preview([intent(), intent(target="out/b.md")])
    assert [step.target for step in result.steps] == ["out/report.md", "out/b.md"]


def test_reading_steps_are_marked_as_harmless():
    result = preview([intent(tool="search", target="the web", writes=False)])
    assert result.steps[0].harmless is True


def test_writing_steps_are_not_harmless():
    assert preview([intent()]).steps[0].harmless is False


def test_the_number_of_changes_is_counted():
    result = preview([intent(), intent(tool="search", writes=False, target="x")])
    assert result.would_change == 1


def test_the_cost_is_estimated_without_being_spent():
    result = preview(
        [
            intent(estimated_cost=Decimal("0.10")),
            intent(target="b", estimated_cost=Decimal("0.25")),
        ]
    )
    assert result.estimated_cost == Decimal("0.35")


def test_steps_needing_approval_are_collected():
    risky = intent(tool="deploy", target="production", needs_approval=True)
    assert preview([intent(), risky]).needs_approval == ("deploy: production",)


def test_nothing_needs_approval_when_nothing_is_risky():
    assert preview([intent()]).needs_approval == ()


def test_steps_that_cannot_be_undone_are_called_out():
    sent = intent(tool="send-email", target="ana", reversible=False)
    assert preview([sent]).permanent == ("send-email: ana",)


def test_a_preview_of_only_reversible_work_has_nothing_permanent():
    assert preview([intent()]).permanent == ()


def test_a_preview_says_plainly_what_it_would_do():
    result = preview([intent(), intent(tool="search", writes=False, target="x")])
    assert result.summary == "1 change, 1 read, about 0.20"


def test_a_preview_of_only_reads_says_nothing_would_change():
    result = preview([intent(tool="search", target="x", writes=False)])
    assert result.summary == "nothing would change"


def test_an_empty_plan_is_refused():
    with pytest.raises(ValueError):
        preview([])


def test_a_preview_can_be_turned_into_a_run():
    assert preview([intent()]).runnable is True


def test_a_preview_whose_steps_all_need_approval_is_not_runnable_yet():
    risky = intent(needs_approval=True)
    assert preview([risky]).runnable is False


def test_a_preview_blocked_on_approval_says_so():
    risky = intent(needs_approval=True)
    assert "approval" in preview([risky]).reason


def test_an_intent_without_a_tool_is_refused():
    with pytest.raises(ValueError):
        intent(tool=" ")


def test_a_negative_estimate_is_refused():
    with pytest.raises(ValueError):
        intent(estimated_cost=Decimal("-1"))
