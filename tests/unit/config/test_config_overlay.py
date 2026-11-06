"""Edits to configuration, kept as versions rather than as a file."""

from __future__ import annotations

import pytest

from agent.src.agent.config.overlay import InMemoryOverlay, NothingToRevertTo

PROMPT = "config/agent/PROMPT.md"
ROUTER = "config/agent/runtime/router.yaml"


@pytest.fixture
def overlay() -> InMemoryOverlay:
    return InMemoryOverlay()


class TestApplyingAnEdit:
    def test_the_content_comes_back(self, overlay):
        overlay.apply(PROMPT, "new wording", author="ada")
        assert overlay.current(PROMPT) == "new wording"

    def test_a_path_never_edited_has_nothing(self, overlay):
        assert overlay.current(PROMPT) is None

    def test_the_first_version_is_one(self, overlay):
        assert overlay.apply(PROMPT, "first", author="ada").version == 1

    def test_versions_count_up_per_path(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        assert overlay.apply(PROMPT, "second", author="ada").version == 2

    def test_each_path_has_its_own_numbering(self, overlay):
        overlay.apply(PROMPT, "a", author="ada")
        overlay.apply(PROMPT, "b", author="ada")
        assert overlay.apply(ROUTER, "c", author="ada").version == 1

    def test_who_and_when_are_recorded(self, overlay):
        written = overlay.apply(PROMPT, "new wording", author="ada")
        assert written.author == "ada"
        assert written.at

    def test_an_edit_needs_an_author(self, overlay):
        with pytest.raises(ValueError):
            overlay.apply(PROMPT, "new wording", author="")


class TestNothingIsOverwritten:
    def test_the_earlier_version_is_still_readable(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        overlay.apply(PROMPT, "second", author="bo")
        assert overlay.at_version(PROMPT, 1).content == "first"

    def test_history_is_oldest_first(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        overlay.apply(PROMPT, "second", author="bo")
        assert [one.content for one in overlay.history(PROMPT)] == ["first", "second"]

    def test_history_names_each_author(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        overlay.apply(PROMPT, "second", author="bo")
        assert [one.author for one in overlay.history(PROMPT)] == ["ada", "bo"]

    def test_an_unedited_path_has_an_empty_history(self, overlay):
        assert overlay.history(PROMPT) == []


class TestReverting:
    def test_it_brings_back_the_old_content(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        overlay.apply(PROMPT, "second", author="bo")
        overlay.revert(PROMPT, to=1, author="cy")
        assert overlay.current(PROMPT) == "first"

    def test_it_writes_a_new_version_rather_than_removing_one(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        overlay.apply(PROMPT, "second", author="bo")
        overlay.revert(PROMPT, to=1, author="cy")
        assert [one.version for one in overlay.history(PROMPT)] == [1, 2, 3]

    def test_the_version_that_was_reverted_is_still_there(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        overlay.apply(PROMPT, "a mistake", author="bo")
        overlay.revert(PROMPT, to=1, author="cy")
        assert overlay.at_version(PROMPT, 2).content == "a mistake"

    def test_the_revert_records_who_did_it(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        overlay.apply(PROMPT, "second", author="bo")
        overlay.revert(PROMPT, to=1, author="cy")
        assert overlay.history(PROMPT)[-1].author == "cy"

    def test_reverting_to_a_version_that_never_existed_is_refused(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        with pytest.raises(NothingToRevertTo):
            overlay.revert(PROMPT, to=7, author="cy")

    def test_reverting_a_path_never_edited_is_refused(self, overlay):
        with pytest.raises(NothingToRevertTo):
            overlay.revert(PROMPT, to=1, author="cy")


class TestAdoptingTheBaseline:
    def test_the_path_stops_being_overridden(self, overlay):
        overlay.apply(PROMPT, "mine", author="ada")
        overlay.adopt_baseline(PROMPT, author="ada")
        assert overlay.current(PROMPT) is None

    def test_it_leaves_a_trace_like_any_other_edit(self, overlay):
        overlay.apply(PROMPT, "mine", author="ada")
        overlay.adopt_baseline(PROMPT, author="bo")
        assert [one.version for one in overlay.history(PROMPT)] == [1, 2]
        assert overlay.history(PROMPT)[-1].author == "bo"

    def test_the_content_it_replaced_is_still_readable(self, overlay):
        overlay.apply(PROMPT, "mine", author="ada")
        overlay.adopt_baseline(PROMPT, author="bo")
        assert overlay.at_version(PROMPT, 1).content == "mine"

    def test_the_path_can_be_overridden_again_afterwards(self, overlay):
        overlay.apply(PROMPT, "mine", author="ada")
        overlay.adopt_baseline(PROMPT, author="bo")
        overlay.apply(PROMPT, "mine again", author="cy")
        assert overlay.current(PROMPT) == "mine again"
        assert [one.version for one in overlay.history(PROMPT)] == [1, 2, 3]


class TestWhichPathsAreOverridden:
    def test_none_to_begin_with(self, overlay):
        assert overlay.overridden() == []

    def test_an_edited_path_is_listed(self, overlay):
        overlay.apply(PROMPT, "mine", author="ada")
        assert overlay.overridden() == [PROMPT]

    def test_a_path_whose_baseline_was_adopted_is_not(self, overlay):
        overlay.apply(PROMPT, "mine", author="ada")
        overlay.adopt_baseline(PROMPT, author="ada")
        assert overlay.overridden() == []

    def test_they_come_back_in_a_stable_order(self, overlay):
        overlay.apply(ROUTER, "r", author="ada")
        overlay.apply(PROMPT, "p", author="ada")
        assert overlay.overridden() == sorted([PROMPT, ROUTER])


class TestContentIsNotInterpreted:
    @pytest.mark.parametrize(
        "awkward", ["", "   ", "not: [valid: yaml", "\x00binary-ish", "ü" * 10]
    )
    def test_whatever_was_given_comes_back_unchanged(self, overlay, awkward):
        overlay.apply(PROMPT, awkward, author="ada")
        assert overlay.current(PROMPT) == awkward
