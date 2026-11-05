"""A placeholder split across stream chunks must still be put back."""

import pytest
from langchain_core.messages import AIMessageChunk

from agent.src.pii.stream_restore import (
    StreamingRestorer,
    StreamRestorers,
    restore_stream_item,
)

MAP = {"[MAIL_1]": "sodutta@redhat.com", "[MAIL_2]": "nirkumar@redhat.com"}


@pytest.fixture
def restorer() -> StreamingRestorer:
    return StreamingRestorer(MAP)


def test_whole_placeholder_in_one_chunk(restorer: StreamingRestorer) -> None:
    assert (
        restorer.feed("Write to [MAIL_1] today") == "Write to sodutta@redhat.com today"
    )


def test_placeholder_split_across_chunks(restorer: StreamingRestorer) -> None:
    out = "".join(restorer.feed(part) for part in ("Write to [MA", "IL_1", "] today"))
    assert out + restorer.flush() == "Write to sodutta@redhat.com today"


def test_split_one_character_at_a_time(restorer: StreamingRestorer) -> None:
    out = "".join(restorer.feed(char) for char in "[MAIL_2]!")
    assert out + restorer.flush() == "nirkumar@redhat.com!"


def test_text_without_a_bracket_is_not_held_back(restorer: StreamingRestorer) -> None:
    assert restorer.feed("The manager is ") == "The manager is "


def test_text_before_a_partial_placeholder_goes_out_at_once(
    restorer: StreamingRestorer,
) -> None:
    assert restorer.feed("Mail [MA") == "Mail "


def test_bracket_that_was_never_a_placeholder_is_released(
    restorer: StreamingRestorer,
) -> None:
    assert restorer.feed("See [the notes] here") == "See [the notes] here"


def test_dangling_bracket_is_released_on_flush(restorer: StreamingRestorer) -> None:
    assert restorer.feed("Ends with [") == "Ends with "
    assert restorer.flush() == "["


def test_long_run_after_a_bracket_cannot_be_a_placeholder(
    restorer: StreamingRestorer,
) -> None:
    tail = "x" * 200
    assert restorer.feed(f"[{tail}") == f"[{tail}"


def test_two_placeholders_in_one_chunk(restorer: StreamingRestorer) -> None:
    assert restorer.feed("[MAIL_1] and [MAIL_2]") == (
        "sodutta@redhat.com and nirkumar@redhat.com"
    )


def test_unknown_placeholder_is_left_alone(restorer: StreamingRestorer) -> None:
    assert restorer.feed("[MAIL_9] stays") + restorer.flush() == "[MAIL_9] stays"


def test_empty_map_passes_everything_through() -> None:
    plain = StreamingRestorer({})
    assert plain.feed("Write to [MAIL_1]") == "Write to [MAIL_1]"
    assert plain.flush() == ""


def test_flush_twice_does_not_repeat_the_held_text(restorer: StreamingRestorer) -> None:
    restorer.feed("Ends with [")
    assert restorer.flush() == "["
    assert restorer.flush() == ""


def item(text: str, message_id: str = "m1") -> tuple:
    return (AIMessageChunk(content=text, id=message_id), {"langgraph_node": "agent"})


def text_of(data: tuple) -> str:
    return data[0].content


def test_restores_a_placeholder_split_across_two_items() -> None:
    restorers = StreamRestorers(MAP)
    first = restore_stream_item(item("Mail [MA"), restorers)
    second = restore_stream_item(item("IL_1] now"), restorers)
    assert text_of(first) + text_of(second) == "Mail sodutta@redhat.com now"


def test_keeps_messages_apart() -> None:
    restorers = StreamRestorers(MAP)
    restore_stream_item(item("[MA", "m1"), restorers)
    assert text_of(restore_stream_item(item("[MAIL_2]", "m2"), restorers)) == (
        "nirkumar@redhat.com"
    )


def test_held_text_is_emitted_when_the_stream_ends() -> None:
    restorers = StreamRestorers(MAP)
    restore_stream_item(item("Ends with ["), restorers)
    assert [text_of(rest) for rest in restorers.flush()] == ["["]


def test_nothing_is_emitted_when_nothing_was_held() -> None:
    restorers = StreamRestorers(MAP)
    restore_stream_item(item("All done"), restorers)
    assert list(restorers.flush()) == []


def test_tool_call_arguments_are_still_restored() -> None:
    restorers = StreamRestorers(MAP)
    chunk = AIMessageChunk(
        content="",
        id="m1",
        tool_calls=[{"name": "send", "args": {"to": "[MAIL_1]"}, "id": "c1"}],
    )
    restored = restore_stream_item((chunk, {}), restorers)
    assert restored[0].tool_calls[0]["args"]["to"] == "sodutta@redhat.com"


def test_takes_in_placeholders_assigned_mid_stream() -> None:
    restorers = StreamRestorers({})
    assert text_of(restore_stream_item(item("Hello "), restorers)) == "Hello "
    restorers.refresh({"[MAIL_3]": "asakala@redhat.com"})
    assert text_of(restore_stream_item(item("[MAIL_3]"), restorers)) == (
        "asakala@redhat.com"
    )
