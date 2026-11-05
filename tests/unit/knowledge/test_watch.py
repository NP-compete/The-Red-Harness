"""Whether a change to a watched source is worth telling anyone about."""

from __future__ import annotations

import pytest

from agent.src.knowledge.watch import Change, Watch, worth_telling


def change(**kwargs) -> Change:
    defaults = {
        "document": "handbook",
        "words_changed": 40,
        "sections_touched": ("expenses",),
        "whitespace_only": False,
        "deleted": False,
        "by": "grace",
    }
    defaults.update(kwargs)
    return Change(**defaults)


def watch(**kwargs) -> Watch:
    defaults = {
        "watcher": "ada",
        "document": "handbook",
        "sections": (),
        "minimum_words": 10,
    }
    defaults.update(kwargs)
    return Watch(**defaults)


def test_a_real_change_to_a_watched_document_is_told():
    assert worth_telling(change(), watch=watch()).tell is True


def test_a_change_to_a_document_nobody_watches_is_not_told():
    elsewhere = change(document="other")
    assert worth_telling(elsewhere, watch=watch()).tell is False


def test_a_reformatting_is_not_a_change_worth_hearing_about():
    tidied = change(whitespace_only=True, words_changed=400)
    assert worth_telling(tidied, watch=watch()).tell is False


def test_a_change_smaller_than_the_watcher_asked_for_is_not_told():
    tiny = change(words_changed=3)
    assert worth_telling(tiny, watch=watch()).tell is False


def test_a_watcher_following_one_section_hears_only_about_that_section():
    elsewhere = change(sections_touched=("travel",))
    assert worth_telling(elsewhere, watch=watch(sections=("expenses",))).tell is False


def test_a_watcher_following_one_section_hears_when_it_changes():
    assert worth_telling(change(), watch=watch(sections=("expenses",))).tell is True


def test_a_change_touching_several_sections_counts_if_one_is_watched():
    broad = change(sections_touched=("travel", "expenses"))
    assert worth_telling(broad, watch=watch(sections=("expenses",))).tell is True


def test_a_deletion_is_always_told_however_small():
    gone = change(deleted=True, words_changed=0)
    assert worth_telling(gone, watch=watch()).tell is True


def test_a_deletion_is_told_even_to_a_section_watcher():
    gone = change(deleted=True, words_changed=0, sections_touched=())
    assert worth_telling(gone, watch=watch(sections=("expenses",))).tell is True


def test_a_watcher_is_not_told_about_their_own_edit():
    mine = change(by="ada")
    assert worth_telling(mine, watch=watch()).tell is False


def test_a_watcher_is_told_about_their_own_deletion_of_nothing():
    mine = change(by="ada", deleted=True)
    assert worth_telling(mine, watch=watch()).tell is False


def test_what_changed_is_summarised():
    told = worth_telling(change(), watch=watch())
    assert told.summary == "handbook changed in expenses"


def test_a_change_with_no_named_section_is_summarised_plainly():
    told = worth_telling(change(sections_touched=()), watch=watch())
    assert told.summary == "handbook changed"


def test_a_deletion_is_summarised_as_a_deletion():
    told = worth_telling(change(deleted=True), watch=watch())
    assert told.summary == "handbook was deleted"


def test_a_change_not_worth_telling_has_nothing_to_summarise():
    assert worth_telling(change(words_changed=3), watch=watch()).summary == ""


def test_a_watch_with_no_document_is_refused():
    with pytest.raises(ValueError):
        watch(document="  ")


def test_a_negative_word_count_is_refused():
    with pytest.raises(ValueError):
        change(words_changed=-1)
