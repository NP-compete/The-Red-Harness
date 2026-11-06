"""Whether what is indexed still matches what exists."""

from __future__ import annotations

import pytest

from agent.src.knowledge.index_sync import Snapshot, State, compare_index


def snapshot(**kwargs) -> Snapshot:
    defaults = {
        "in_source": ("a", "b", "c"),
        "indexed": ("a", "b", "c"),
        "failed": (),
    }
    defaults.update(kwargs)
    return Snapshot(**defaults)


def test_a_matching_index_is_in_step():
    assert compare_index(snapshot()).state is State.IN_STEP


def test_a_matching_index_has_nothing_outstanding():
    result = compare_index(snapshot())
    assert result.missing == () and result.orphaned == ()


def test_a_document_that_was_never_indexed_is_missing():
    assert compare_index(snapshot(indexed=("a", "b"))).missing == ("c",)


def test_a_document_no_longer_in_the_source_is_orphaned():
    assert compare_index(snapshot(indexed=("a", "b", "c", "gone"))).orphaned == (
        "gone",
    )


def test_an_index_with_gaps_is_behind():
    assert compare_index(snapshot(indexed=("a", "b"))).state is State.BEHIND


def test_an_index_holding_removed_documents_needs_tidying():
    assert (
        compare_index(snapshot(indexed=("a", "b", "c", "gone"))).state
        is State.NEEDS_TIDYING
    )


def test_missing_documents_matter_more_than_orphaned_ones():
    both = snapshot(indexed=("a", "gone"))
    assert compare_index(both).state is State.BEHIND


def test_documents_that_failed_to_index_are_reported():
    assert compare_index(snapshot(indexed=("a", "b"), failed=("c",))).failed == ("c",)


def test_a_failed_document_is_not_also_called_missing():
    assert compare_index(snapshot(indexed=("a", "b"), failed=("c",))).missing == ()


def test_an_index_with_failures_is_broken():
    assert (
        compare_index(snapshot(indexed=("a", "b"), failed=("c",))).state is State.BROKEN
    )


def test_failures_matter_more_than_gaps():
    both = snapshot(in_source=("a", "b", "c", "d"), indexed=("a",), failed=("b",))
    assert compare_index(both).state is State.BROKEN


def test_how_much_is_covered_is_reported():
    assert compare_index(snapshot(indexed=("a", "b"))).coverage == pytest.approx(2 / 3)


def test_an_empty_source_is_fully_covered():
    assert compare_index(snapshot(in_source=(), indexed=())).coverage == 1.0


def test_an_empty_source_with_leftovers_still_needs_tidying():
    assert (
        compare_index(snapshot(in_source=(), indexed=("gone",))).state
        is State.NEEDS_TIDYING
    )


def test_whether_it_is_safe_to_answer_from_is_reported():
    assert compare_index(snapshot()).trustworthy is True


def test_an_index_with_gaps_is_not_safe_to_answer_from():
    assert compare_index(snapshot(indexed=("a",))).trustworthy is False


def test_an_index_with_only_leftovers_is_still_safe_to_answer_from():
    assert compare_index(snapshot(indexed=("a", "b", "c", "gone"))).trustworthy is True


def test_a_document_both_indexed_and_failed_is_refused():
    with pytest.raises(ValueError):
        Snapshot(in_source=("a",), indexed=("a",), failed=("a",))
