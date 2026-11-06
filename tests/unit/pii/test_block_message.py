"""What a person is told when their question is refused."""

from __future__ import annotations

from agent.src.pii.block_message import blocked_reply


class Match:
    def __init__(self, label: str, start: int, end: int) -> None:
        self.label, self.start, self.end = label, start, end


SENTENCE = "Tell me the North revenue for the Dublin office."


class TestWhatItSays:
    def test_it_names_the_kind_of_thing_found(self):
        said = blocked_reply(SENTENCE, [Match("ADDRESS", 12, 17)])
        assert "ADDRESS" in said

    def test_it_quotes_the_words_that_triggered_it(self):
        said = blocked_reply(SENTENCE, [Match("ADDRESS", 12, 17)])
        assert "North" in said

    def test_it_quotes_every_one_of_them(self):
        said = blocked_reply(
            SENTENCE, [Match("ADDRESS", 12, 17), Match("ADDRESS", 34, 40)]
        )
        assert "North" in said and "Dublin" in said

    def test_it_says_what_to_do(self):
        said = blocked_reply(SENTENCE, [Match("ADDRESS", 12, 17)])
        assert "try again" in said.lower()

    def test_the_same_word_twice_is_quoted_once(self):
        text = "North and North again"
        said = blocked_reply(text, [Match("ADDRESS", 0, 5), Match("ADDRESS", 10, 15)])
        assert said.count('"North"') == 1


class TestWhenItCannotQuote:
    def test_a_match_outside_the_text_does_not_break_the_reply(self):
        said = blocked_reply("short", [Match("ADDRESS", 100, 120)])
        assert "ADDRESS" in said

    def test_an_empty_span_is_skipped_rather_than_quoted_blank(self):
        said = blocked_reply(SENTENCE, [Match("ADDRESS", 5, 5)])
        assert '""' not in said

    def test_nothing_found_is_still_a_sentence(self):
        assert blocked_reply(SENTENCE, [])


class TestItDoesNotRunOn:
    def test_a_long_match_is_shortened(self):
        text = "x" * 400
        said = blocked_reply(text, [Match("ADDRESS", 0, 400)])
        assert len(said) < 300

    def test_many_matches_do_not_make_an_essay(self):
        text = " ".join(f"word{i}" for i in range(50))
        matches = [Match("ADDRESS", i * 7, i * 7 + 6) for i in range(50)]
        assert len(blocked_reply(text, matches)) < 400
