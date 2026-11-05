"""Working out how a tool's result is best shown."""

from __future__ import annotations

import pytest

from agent.src.agent.result_shape import Shape, describe_result


def test_rows_of_the_same_keys_are_a_table():
    rows = [{"name": "a", "cost": 1}, {"name": "b", "cost": 2}]
    assert describe_result(rows).shape is Shape.TABLE


def test_a_table_reports_its_columns():
    rows = [{"name": "a", "cost": 1}, {"name": "b", "cost": 2}]
    assert describe_result(rows).columns == ("cost", "name")


def test_a_table_reports_how_many_rows():
    rows = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    assert describe_result(rows).rows == 3


def test_rows_with_different_keys_are_not_a_table():
    rows = [{"name": "a"}, {"cost": 2}]
    assert describe_result(rows).shape is Shape.JSON


def test_a_single_object_is_shown_as_fields():
    assert describe_result({"name": "a", "cost": 1}).shape is Shape.FIELDS


def test_a_list_of_plain_values_is_a_list():
    assert describe_result(["a", "b", "c"]).shape is Shape.LIST


def test_plain_prose_is_text():
    assert describe_result("The limit is 500.").shape is Shape.TEXT


def test_something_that_looks_like_code_is_code():
    assert describe_result("def add(a, b):\n    return a + b\n").shape is Shape.CODE


def test_code_reports_its_language_when_it_can_tell():
    assert describe_result("def add(a, b):\n    return a + b\n").language == "python"


def test_text_reports_no_language():
    assert describe_result("The limit is 500.").language == ""


def test_an_empty_result_is_reported_as_empty():
    assert describe_result([]).shape is Shape.EMPTY


def test_an_empty_string_is_empty_too():
    assert describe_result("   ").shape is Shape.EMPTY


def test_a_very_large_table_says_it_should_be_paged():
    rows = [{"n": index} for index in range(500)]
    assert describe_result(rows).needs_paging is True


def test_a_small_table_needs_no_paging():
    assert describe_result([{"n": 1}]).needs_paging is False


def test_a_very_long_text_says_it_should_be_collapsed():
    assert describe_result("word " * 2000).needs_collapsing is True


def test_a_short_text_needs_no_collapsing():
    assert describe_result("The limit is 500.").needs_collapsing is False


def test_a_nested_structure_falls_back_to_json():
    assert describe_result({"a": {"b": {"c": 1}}}).shape is Shape.JSON


def test_something_unprintable_is_refused():
    with pytest.raises(ValueError):
        describe_result(object())
