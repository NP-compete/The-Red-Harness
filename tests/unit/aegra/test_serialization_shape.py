"""What shape a tool result is, said once where it is serialised."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, ToolMessage

from agent.aegra.serialization import serialize_message


def shape_of(content) -> dict:
    text = content if isinstance(content, str) else json.dumps(content)
    return serialize_message(ToolMessage(content=text, tool_call_id="c1")).get(
        "shape", {}
    )


def test_a_plain_sentence_is_text():
    assert shape_of("The travel limit is 500 euros.")["kind"] == "text"


def test_rows_sharing_their_keys_are_a_table():
    rows = [{"name": "ada", "team": "platform"}, {"name": "grace", "team": "payments"}]
    assert shape_of(rows)["kind"] == "table"


def test_the_columns_of_a_table_are_named():
    rows = [{"name": "ada", "team": "platform"}, {"name": "grace", "team": "payments"}]
    assert shape_of(rows)["columns"] == ["name", "team"]


def test_how_many_rows_there_are_is_reported():
    rows = [{"a": 1}, {"a": 2}, {"a": 3}]
    assert shape_of(rows)["rows"] == 3


def test_a_long_table_says_it_needs_paging():
    rows = [{"a": i} for i in range(150)]
    assert shape_of(rows)["needs_paging"] is True


def test_a_short_table_does_not():
    assert shape_of([{"a": 1}])["needs_paging"] is False


def test_an_empty_result_says_so():
    assert shape_of("")["kind"] == "empty"


def test_a_long_answer_says_it_needs_folding():
    assert shape_of(" ".join(["word"] * 600))["needs_collapsing"] is True


def test_an_answer_message_carries_no_shape():
    assert "shape" not in serialize_message(AIMessage(content="hello"))


def test_unreadable_content_is_survived():
    assert shape_of("{not json")["kind"] in {"text", "code", "json"}
