"""Taking back what a subagent produced."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.agent.subagent_result import Returned, Verdict, accept_result


def returned(**kwargs) -> Returned:
    defaults = {
        "child": "researcher",
        "answer": "The limit is 500.",
        "sources": ("handbook",),
        "read_untrusted": False,
        "cost": Decimal("0.40"),
        "failed": False,
        "reason": "",
    }
    defaults.update(kwargs)
    return Returned(**defaults)


def test_an_ordinary_result_is_taken():
    assert accept_result(returned()).verdict is Verdict.ACCEPTED


def test_the_answer_comes_back():
    assert accept_result(returned()).answer == "The limit is 500."


def test_the_sources_come_back_with_it():
    assert accept_result(returned()).sources == ("handbook",)


def test_the_cost_is_added_to_the_parent():
    assert accept_result(returned()).cost == Decimal("0.40")


def test_a_failed_child_is_not_accepted():
    broken = returned(failed=True, answer="", reason="the search tool was unavailable")
    assert accept_result(broken).verdict is Verdict.FAILED


def test_a_failed_child_still_reports_what_it_cost():
    broken = returned(failed=True, answer="", reason="x", cost=Decimal("0.20"))
    assert accept_result(broken).cost == Decimal("0.20")


def test_a_failed_child_says_why():
    broken = returned(failed=True, answer="", reason="the search tool was unavailable")
    assert "search tool" in accept_result(broken).reason


def test_an_answer_with_no_sources_is_taken_but_marked():
    loose = returned(sources=())
    assert accept_result(loose).verdict is Verdict.UNSOURCED


def test_an_unsourced_answer_is_still_usable():
    assert accept_result(returned(sources=())).answer == "The limit is 500."


def test_a_child_that_read_untrusted_material_taints_its_answer():
    tainted = returned(read_untrusted=True)
    assert accept_result(tainted).trusted is False


def test_a_child_that_read_nothing_untrusted_returns_trusted_work():
    assert accept_result(returned()).trusted is True


def test_a_tainted_answer_is_still_accepted():
    assert accept_result(returned(read_untrusted=True)).verdict is Verdict.ACCEPTED


def test_an_empty_answer_from_a_child_that_did_not_fail_is_nothing_useful():
    assert accept_result(returned(answer="   ")).verdict is Verdict.EMPTY


def test_an_empty_answer_is_not_passed_on_as_text():
    assert accept_result(returned(answer="   ")).answer == ""


def test_whether_the_parent_should_retry_is_reported():
    broken = returned(failed=True, answer="", reason="the search tool was unavailable")
    assert accept_result(broken).worth_retrying is True


def test_an_accepted_result_is_not_worth_retrying():
    assert accept_result(returned()).worth_retrying is False


def test_an_empty_answer_is_worth_asking_again_for():
    assert accept_result(returned(answer="")).worth_retrying is True


def test_a_failed_child_with_no_reason_is_refused():
    with pytest.raises(ValueError):
        returned(failed=True, answer="", reason="  ")


def test_a_negative_cost_is_refused():
    with pytest.raises(ValueError):
        returned(cost=Decimal("-1"))
