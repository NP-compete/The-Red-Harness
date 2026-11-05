"""Telling someone what a run did, once it has finished."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from agent.src.agent.run_report import Ending, Outcome, build_report


def ending(**kwargs) -> Ending:
    defaults = {
        "finished": True,
        "steps_done": 4,
        "steps_total": 4,
        "elapsed": timedelta(seconds=90),
        "cost": Decimal("1.25"),
        "changes": ("file-written: out/report.md",),
        "permanent_changes": (),
        "unanswered_parts": (),
        "unsupported_claims": (),
        "failed_step": "",
        "stopped_by": "",
    }
    defaults.update(kwargs)
    return Ending(**defaults)


def test_a_clean_run_is_reported_as_done():
    assert build_report(ending()).outcome is Outcome.DONE


def test_a_clean_run_says_what_it_changed():
    assert build_report(ending()).changes == ("file-written: out/report.md",)


def test_a_clean_run_reports_what_it_cost():
    assert build_report(ending()).cost == Decimal("1.25")


def test_a_run_that_failed_is_reported_as_failed():
    report = build_report(ending(finished=False, failed_step="gather", steps_done=1))
    assert report.outcome is Outcome.FAILED


def test_a_failed_run_names_the_step():
    report = build_report(ending(finished=False, failed_step="gather", steps_done=1))
    assert "gather" in report.headline


def test_a_run_someone_stopped_is_reported_as_stopped():
    report = build_report(ending(finished=False, stopped_by="ana", steps_done=2))
    assert report.outcome is Outcome.STOPPED


def test_a_stopped_run_says_who_stopped_it():
    report = build_report(ending(finished=False, stopped_by="ana", steps_done=2))
    assert "ana" in report.headline


def test_a_run_that_finished_with_gaps_is_reported_as_partial():
    report = build_report(ending(unanswered_parts=("who approves it",)))
    assert report.outcome is Outcome.PARTIAL


def test_a_partial_run_names_what_is_missing():
    report = build_report(ending(unanswered_parts=("who approves it",)))
    assert report.gaps == ("who approves it",)


def test_unsupported_claims_make_a_run_partial_too():
    report = build_report(ending(unsupported_claims=("made up thing",)))
    assert report.outcome is Outcome.PARTIAL


def test_failure_outranks_a_gap():
    report = build_report(
        ending(finished=False, failed_step="gather", unanswered_parts=("a",))
    )
    assert report.outcome is Outcome.FAILED


def test_what_cannot_be_undone_is_called_out():
    report = build_report(ending(permanent_changes=("email-sent: ana",)))
    assert report.permanent == ("email-sent: ana",)


def test_a_run_with_permanent_changes_cannot_be_undone():
    assert (
        build_report(ending(permanent_changes=("email-sent: ana",))).reversible is False
    )


def test_a_run_of_reversible_changes_can_be_undone():
    assert build_report(ending()).reversible is True


def test_a_run_that_changed_nothing_has_nothing_to_undo():
    assert build_report(ending(changes=())).reversible is False


def test_how_long_it_took_is_reported_plainly():
    assert build_report(ending()).took == "1m 30s"


def test_a_short_run_is_reported_in_seconds():
    assert build_report(ending(elapsed=timedelta(seconds=9))).took == "9s"


def test_whether_anything_needs_attention_is_reported():
    assert build_report(ending(unsupported_claims=("x",))).needs_attention is True


def test_a_clean_run_needs_no_attention():
    assert build_report(ending()).needs_attention is False


def test_a_run_that_neither_finished_nor_failed_is_refused():
    with pytest.raises(ValueError):
        Ending(
            finished=False,
            steps_done=1,
            steps_total=4,
            elapsed=timedelta(seconds=1),
            cost=Decimal("0"),
            changes=(),
            permanent_changes=(),
            unanswered_parts=(),
            unsupported_claims=(),
            failed_step="",
            stopped_by="",
        )
