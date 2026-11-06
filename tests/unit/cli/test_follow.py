"""E28-T4. Watching an answer arrive."""

from __future__ import annotations

import json

from agent.cli.follow import follow, pause_in, text_in


def sse(event: str, data: object) -> list[str]:
    return [f"event: {event}", f"data: {json.dumps(data)}", ""]


def chunk(text: str) -> list[str]:
    return sse("messages/partial", [{"type": "ai", "content": text}])


class TestReadingAFrame:
    def test_a_message_frame_is_text(self):
        assert (
            text_in("messages/partial", [{"type": "ai", "content": "hello"}]) == "hello"
        )

    def test_a_metadata_frame_is_not(self):
        """Printing metadata between the words gives a terminal"""
        assert text_in("metadata", {"run_id": "r1"}) == ""

    def test_the_block_form_is_read_too(self):
        said = text_in(
            "messages/partial",
            [{"type": "ai", "content": [{"type": "text", "text": "hi"}]}],
        )
        assert said == "hi"

    def test_a_tool_message_is_not_the_answer(self):
        assert text_in("messages/partial", [{"type": "tool", "content": "ran"}]) == ""


class TestFollowing:
    def test_it_prints_as_it_goes(self):
        printed: list[str] = []
        lines = chunk("Hello") + chunk(" there")
        found = follow(iter(lines), thread_id="t1", write=printed.append)
        assert printed == ["Hello", " there"]
        assert found.text == "Hello there"

    def test_a_repeated_prefix_is_printed_once(self):
        """Some frames carry the answer so far rather than the"""
        printed: list[str] = []
        lines = chunk("Hello") + chunk("Hello there")
        found = follow(iter(lines), thread_id="t1", write=printed.append)
        assert "".join(printed) == "Hello there"
        assert found.text == "Hello there"

    def test_an_unreadable_frame_does_not_end_the_run(self):
        printed: list[str] = []
        lines = ["event: messages/partial", "data: {not json", ""] + chunk("still here")
        found = follow(iter(lines), thread_id="t1", write=printed.append)
        assert found.text == "still here"

    def test_the_done_marker_is_not_text(self):
        printed: list[str] = []
        found = follow(
            iter(chunk("done") + ["data: [DONE]", ""]),
            thread_id="t1",
            write=printed.append,
        )
        assert found.text == "done"


class TestAPause:
    def test_it_ends_the_stream(self):
        """A follower that waited quietly for more text would look"""
        printed: list[str] = []
        interrupt = {
            "__interrupt__": [
                {"value": {"action_requests": [{"name": "write_file", "args": {}}]}}
            ]
        }
        lines = chunk("about to ") + sse("values", interrupt) + chunk("never printed")
        found = follow(iter(lines), thread_id="t1", write=printed.append)
        assert found.paused is not None
        assert "never printed" not in "".join(printed)

    def test_it_is_the_shape_ask_reports(self):
        """The first version invented its own, and the command"""
        found = pause_in(
            {
                "__interrupt__": [
                    {"value": {"action_requests": [{"name": "write_file", "args": {}}]}}
                ]
            },
            thread_id="t1",
        )
        assert found is not None
        assert "awaiting" in found
        assert found["awaiting"][0]["action"] == "write_file"
