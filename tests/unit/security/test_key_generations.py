"""Opening something sealed by a key that has since been replaced."""

from __future__ import annotations

import pytest

from agent.src.security.key_generations import NoKeyOpensIt, open_with


def _opener(correct: str):
    """A stand-in for a decrypt: works for one key, raises otherwise."""

    def open_it(key: str, sealed: str) -> str:
        if key != correct:
            raise ValueError("wrong key")
        return f"opened:{sealed}"

    return open_it


class TestTheCurrentKey:
    def test_it_is_tried_first(self):
        tried: list[str] = []

        def open_it(key: str, sealed: str) -> str:
            tried.append(key)
            return "opened"

        open_with(["current", "previous"], "sealed", open_it)
        assert tried == ["current"]

    def test_what_it_opens_comes_back(self):
        found = open_with(["current"], "sealed", _opener("current"))
        assert found == "opened:sealed"


class TestTheKeyItReplaced:
    def test_something_sealed_before_a_rotation_still_opens(self):
        found = open_with(["current", "previous"], "sealed", _opener("previous"))
        assert found == "opened:sealed"

    def test_the_current_key_is_still_tried_first(self):
        tried: list[str] = []

        def open_it(key: str, sealed: str) -> str:
            tried.append(key)
            if key != "previous":
                raise ValueError("wrong key")
            return "opened"

        open_with(["current", "previous"], "sealed", open_it)
        assert tried == ["current", "previous"]


class TestWhenNothingOpensIt:
    def test_it_raises(self):
        with pytest.raises(NoKeyOpensIt):
            open_with(["current", "previous"], "sealed", _opener("neither"))

    def test_no_keys_at_all_raises_too(self):
        with pytest.raises(NoKeyOpensIt):
            open_with([], "sealed", _opener("anything"))

    def test_the_failure_does_not_quote_a_key(self):
        with pytest.raises(NoKeyOpensIt) as raised:
            open_with(["a-real-key"], "sealed", _opener("other"))
        assert "a-real-key" not in str(raised.value)

    def test_the_failure_does_not_quote_the_sealed_value(self):
        with pytest.raises(NoKeyOpensIt) as raised:
            open_with(["key"], "the-sealed-bytes", _opener("other"))
        assert "the-sealed-bytes" not in str(raised.value)


class TestItDoesNotAccumulate:
    def test_only_the_keys_it_was_given_are_tried(self):
        tried: list[str] = []

        def open_it(key: str, sealed: str) -> str:
            tried.append(key)
            raise ValueError("wrong key")

        with pytest.raises(NoKeyOpensIt):
            open_with(["one", "two"], "sealed", open_it)
        assert tried == ["one", "two"]

    def test_blank_and_repeated_keys_are_skipped(self):
        tried: list[str] = []

        def open_it(key: str, sealed: str) -> str:
            tried.append(key)
            raise ValueError("wrong key")

        with pytest.raises(NoKeyOpensIt):
            open_with(["one", "", "one", "two", None], "sealed", open_it)
        assert tried == ["one", "two"]
