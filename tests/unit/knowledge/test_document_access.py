"""Dropping what the asker may not read before an answer is written."""

from __future__ import annotations

import pytest

from agent.src.knowledge.document_access import Asker, Hit, filter_hits


def hit(**kwargs) -> Hit:
    defaults = {
        "chunk": "c1",
        "document": "handbook",
        "readers": ("ada",),
        "listable_by": ("ada",),
    }
    defaults.update(kwargs)
    return Hit(**defaults)


def asker(**kwargs) -> Asker:
    defaults = {"person": "ada", "groups": ()}
    defaults.update(kwargs)
    return Asker(**defaults)


def test_a_document_the_asker_may_read_is_kept():
    assert filter_hits([hit()], asker=asker()).usable == ["c1"]


def test_a_document_the_asker_may_not_read_is_dropped():
    closed = hit(readers=("grace",), listable_by=("grace",))
    assert filter_hits([closed], asker=asker()).usable == []


def test_access_through_a_group_is_access():
    shared = hit(readers=("platform",), listable_by=("platform",))
    assert filter_hits([shared], asker=asker(groups=("platform",))).usable == ["c1"]


def test_a_withheld_document_is_counted():
    closed = hit(readers=("grace",), listable_by=("grace",))
    assert filter_hits([closed], asker=asker()).withheld == 1


def test_a_withheld_document_the_asker_may_know_exists_is_named():
    closed = hit(readers=("grace",), listable_by=("ada",))
    assert filter_hits([closed], asker=asker()).requestable == ["handbook"]


def test_a_document_the_asker_may_not_know_exists_is_never_named():
    hidden = hit(readers=("grace",), listable_by=("grace",))
    assert filter_hits([hidden], asker=asker()).requestable == []


def test_a_document_the_asker_may_not_know_exists_is_still_counted():
    hidden = hit(readers=("grace",), listable_by=("grace",))
    assert filter_hits([hidden], asker=asker()).withheld == 1


def test_a_document_is_named_once_however_many_pieces_of_it_were_found():
    closed = [
        hit(chunk="c1", readers=("grace",), listable_by=("ada",)),
        hit(chunk="c2", readers=("grace",), listable_by=("ada",)),
    ]
    assert filter_hits(closed, asker=asker()).requestable == ["handbook"]


def test_every_withheld_piece_is_counted_even_from_one_document():
    closed = [
        hit(chunk="c1", readers=("grace",), listable_by=("ada",)),
        hit(chunk="c2", readers=("grace",), listable_by=("ada",)),
    ]
    assert filter_hits(closed, asker=asker()).withheld == 2


def test_the_order_found_is_kept():
    hits = [hit(chunk="c2"), hit(chunk="c1")]
    assert filter_hits(hits, asker=asker()).usable == ["c2", "c1"]


def test_an_answer_built_on_nothing_says_everything_was_withheld():
    closed = hit(readers=("grace",), listable_by=("ada",))
    result = filter_hits([closed], asker=asker())
    assert result.nothing_left is True


def test_an_answer_with_something_left_does_not_say_that():
    assert filter_hits([hit()], asker=asker()).nothing_left is False


def test_finding_nothing_at_all_is_not_the_same_as_being_withheld():
    result = filter_hits([], asker=asker())
    assert (result.nothing_left, result.withheld) == (False, 0)


def test_a_document_with_no_readers_at_all_is_refused():
    with pytest.raises(ValueError):
        hit(readers=())


def test_an_asker_with_no_identity_is_refused():
    with pytest.raises(ValueError):
        asker(person="  ")
