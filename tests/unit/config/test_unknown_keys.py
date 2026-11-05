"""A key nothing reads is a setting that was never applied."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agent.src.agent.config.unknown_keys import unknown_keys


class Inner(BaseModel):
    depth: int = 1


class Entry(BaseModel):
    name: str = ""


class Outer(BaseModel):
    enabled: bool = False
    inner: Inner = Field(default_factory=Inner)
    optional_inner: Inner | None = None
    entries: list[Entry] = Field(default_factory=list)
    free_form: dict[str, int] = Field(default_factory=dict)
    anything: list = Field(default_factory=list)


class TestNothingUnexpected:
    def test_an_empty_section_is_fine(self):
        assert unknown_keys({}, Outer) == []

    def test_every_key_recognised_is_fine(self):
        assert unknown_keys({"enabled": True, "inner": {"depth": 2}}, Outer) == []

    def test_a_free_form_mapping_may_hold_anything(self):
        assert unknown_keys({"free_form": {"whatever": 1}}, Outer) == []

    def test_a_list_of_anything_is_not_inspected(self):
        assert unknown_keys({"anything": [{"x": 1}]}, Outer) == []

    def test_something_that_is_not_a_mapping_is_left_alone(self):
        assert unknown_keys({"inner": "not a mapping"}, Outer) == []


class TestAKeyNothingReads:
    def test_an_unknown_key_is_found(self):
        assert unknown_keys({"enabled_typo": True}, Outer)

    def test_it_is_named(self):
        assert "enabled_typo" in unknown_keys({"enabled_typo": True}, Outer)[0]

    def test_an_unknown_key_inside_a_section_is_found(self):
        found = unknown_keys({"inner": {"depht": 2}}, Outer)
        assert len(found) == 1

    def test_a_nested_key_is_named_with_its_parent(self):
        found = unknown_keys({"inner": {"depht": 2}}, Outer)
        assert "inner.depht" in found[0]

    def test_it_starts_from_the_section_it_was_given(self):
        found = unknown_keys({"depht": 2}, Inner, path="middleware.inner")
        assert "middleware.inner.depht" in found[0]

    def test_every_unknown_key_is_reported(self):
        assert len(unknown_keys({"a": 1, "b": 2}, Outer)) == 2

    def test_an_unknown_key_in_a_list_entry_is_found(self):
        found = unknown_keys({"entries": [{"name": "a"}, {"nmae": "b"}]}, Outer)
        assert "entries.nmae" in found[0]

    def test_an_optional_section_is_still_inspected(self):
        found = unknown_keys({"optional_inner": {"depht": 1}}, Outer)
        assert "optional_inner.depht" in found[0]

    def test_a_known_key_beside_an_unknown_one_is_not_reported(self):
        found = unknown_keys({"enabled": True, "enabledd": True}, Outer)
        assert len(found) == 1 and "enabledd" in found[0]
