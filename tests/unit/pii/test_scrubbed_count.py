"""What "PII scrubbed: N" means, and what it used to mean."""

from __future__ import annotations

from agent.src.pii.middleware import _text_of, _tokens_in_this_turn


class _Message:
    def __init__(self, content, kind="human"):
        self.content = content
        self.type = kind


MAP = {"[MAIL_1]": "ada@example.com", "[MAIL_2]": "bo@example.org"}


class TestCounting:
    def test_it_counts_what_the_reader_just_wrote(self):
        said = [_Message("mail [MAIL_1] and [MAIL_2]")]
        assert _tokens_in_this_turn(MAP, said) == 2

    def test_a_message_with_nothing_in_it_counts_nothing(self):
        assert _tokens_in_this_turn(MAP, [_Message("no addresses here")]) == 0

    def test_earlier_turns_do_not_keep_adding_up(self):
        """The history goes to the model on every turn and still"""
        conversation = [
            _Message("mail [MAIL_1] and [MAIL_2]"),
            _Message("", kind="ai"),
            _Message("thanks, nothing else"),
        ]
        assert _tokens_in_this_turn(MAP, conversation) == 0

    def test_the_whole_map_is_not_the_answer(self):
        """A value scrubbed out of the system prompt is in the map"""
        bigger = {**MAP, "[MAIL_9]": "support@example.com"}
        assert _tokens_in_this_turn(bigger, [_Message("mail [MAIL_1]")]) == 1

    def test_no_substitutions_at_all_is_zero(self):
        assert _tokens_in_this_turn({}, [_Message("anything")]) == 0

    def test_a_conversation_with_no_human_message_is_zero(self):
        assert _tokens_in_this_turn(MAP, [_Message("[MAIL_1]", kind="ai")]) == 0


class TestReadingContent:
    def test_a_plain_string(self):
        assert _text_of("hello") == "hello"

    def test_the_block_form(self):
        """Content is a list of blocks on some messages, and a"""
        assert "hello" in _text_of([{"type": "text", "text": "hello"}])

    def test_anything_else_is_empty_rather_than_an_error(self):
        assert _text_of(None) == ""
