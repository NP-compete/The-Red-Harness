"""An edit takes effect, and a run already going is left alone."""

from __future__ import annotations

import pytest

from agent.aegra.graph import _graph_fingerprint
from agent.src.agent.config.overlay import InMemoryOverlay
from agent.src.agent.config.resolution import use_overlay

PROMPT = "config/agent/PROMPT.md"


@pytest.fixture(autouse=True)
def _clean():
    use_overlay(None)
    yield
    use_overlay(None)


def _print() -> str:
    return _graph_fingerprint("gemini", "a prompt", ["search"])


class TestTheMarkChangesWithAnyEdit:
    def test_an_edit_changes_the_fingerprint(self):
        overlay = InMemoryOverlay()
        use_overlay(overlay)
        before = _print()
        overlay.apply(PROMPT, "new wording", author="ada")
        assert _print() != before

    def test_a_second_edit_changes_it_again(self):
        overlay = InMemoryOverlay()
        use_overlay(overlay)
        overlay.apply(PROMPT, "one", author="ada")
        after_one = _print()
        overlay.apply(PROMPT, "two", author="ada")
        assert _print() != after_one

    def test_adopting_the_baseline_changes_it(self):
        overlay = InMemoryOverlay()
        use_overlay(overlay)
        overlay.apply(PROMPT, "mine", author="ada")
        after_edit = _print()
        overlay.adopt_baseline(PROMPT, author="ada")
        assert _print() != after_edit

    def test_a_revert_changes_it(self):
        overlay = InMemoryOverlay()
        use_overlay(overlay)
        overlay.apply(PROMPT, "one", author="ada")
        overlay.apply(PROMPT, "two", author="ada")
        after_two = _print()
        overlay.revert(PROMPT, to=1, author="ada")
        assert _print() != after_two

    def test_an_edit_to_a_file_the_fingerprint_never_named_still_changes_it(self):
        overlay = InMemoryOverlay()
        use_overlay(overlay)
        before = _print()
        overlay.apply("config/agent/skills/data-discovery/SKILL.md", "x", author="ada")
        assert _print() != before


class TestNothingElseChanges:
    def test_with_no_overlay_the_fingerprint_is_what_it_always_was(self):
        use_overlay(None)
        first = _print()
        use_overlay(None)
        assert _print() == first

    def test_an_overlay_holding_nothing_does_not_change_it(self):
        use_overlay(None)
        bare = _print()
        use_overlay(InMemoryOverlay())
        assert _print() == bare

    def test_the_same_configuration_still_shares_a_graph(self):
        overlay = InMemoryOverlay()
        use_overlay(overlay)
        overlay.apply(PROMPT, "settled", author="ada")
        assert _print() == _print()

    def test_different_requests_still_key_differently(self):
        assert _graph_fingerprint("gemini", "a", []) != _graph_fingerprint(
            "gemini", "b", []
        )


class TestARunAlreadyGoingIsLeftAlone:
    def test_a_fingerprint_taken_before_an_edit_still_names_that_graph(self):
        """A run resolves its graph once and keeps it."""
        overlay = InMemoryOverlay()
        use_overlay(overlay)
        taken = _print()

        overlay.apply(PROMPT, "changed mid-run", author="ada")

        assert _print() != taken
        assert taken and len(taken) == 16
