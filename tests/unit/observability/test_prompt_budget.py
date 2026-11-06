"""What a turn spends before the person has said anything."""

from __future__ import annotations

import pytest

from agent.src.observability.prompt_budget import share_of_prompt, summarise_turn


class TestWhatTheFixedWeightIs:
    def test_a_turn_reports_what_it_sent(self):
        turn = summarise_turn(input_tokens=9035, output_tokens=3, question="hello")
        assert turn.input_tokens == 9035

    def test_the_question_is_a_rounding_error_beside_the_prompt(self):
        turn = summarise_turn(input_tokens=9035, output_tokens=3, question="hi there")
        assert turn.overhead_share > 0.99

    def test_a_long_question_takes_a_larger_share(self):
        turn = summarise_turn(input_tokens=200, output_tokens=3, question="word " * 100)
        assert turn.overhead_share < 0.5

    def test_a_turn_with_no_question_is_all_overhead(self):
        turn = summarise_turn(input_tokens=500, output_tokens=1, question="")
        assert turn.overhead_share == 1.0


class TestShareOfPrompt:
    def test_a_section_is_measured_against_the_whole(self):
        assert share_of_prompt(2000, 10000) == pytest.approx(0.2)

    def test_an_empty_prompt_has_no_shares_rather_than_dividing_by_zero(self):
        assert share_of_prompt(10, 0) == 0.0

    def test_a_section_larger_than_the_prompt_is_reported_as_all_of_it(self):
        assert share_of_prompt(50, 10) == 1.0


class TestWhereTheWeightSits:
    """A total says a turn is expensive; a split says what to change."""

    PROMPT = (
        "You are an assistant. " + "x" * 400 + "\n"
        "# Skills\n" + "y" * 200 + "\n"
        "<agent_memory>\nteal\n</agent_memory>\n"
        '{"name": "read_file", "parameters": {}}'
    )

    def test_it_names_the_sections_it_found(self):
        from agent.src.observability.prompt_budget import split_prompt

        assert set(split_prompt(self.PROMPT)) >= {"instructions", "skills", "memory"}

    def test_the_instructions_are_the_largest_part_here(self):
        from agent.src.observability.prompt_budget import split_prompt

        found = split_prompt(self.PROMPT)
        assert found["instructions"] > found["skills"]

    def test_a_section_the_prompt_does_not_carry_is_absent(self):
        from agent.src.observability.prompt_budget import split_prompt

        assert "skills" not in split_prompt("You are an assistant, and nothing else.")

    def test_the_parts_add_up_to_the_whole(self):
        from agent.src.observability.prompt_budget import split_prompt

        assert sum(split_prompt(self.PROMPT).values()) == len(self.PROMPT)

    def test_an_empty_prompt_splits_into_nothing(self):
        from agent.src.observability.prompt_budget import split_prompt

        assert split_prompt("") == {}


class TestWhatWasBilledIsNotWhatWasSent:
    """A warm cache bills less than it sends."""

    def test_the_prompt_is_what_was_sent_plus_what_was_cached(self):
        turn = summarise_turn(
            input_tokens=5182, output_tokens=3, question="hi", cached_tokens=3853
        )
        assert turn.prompt_tokens == 9035

    def test_a_cold_call_sends_exactly_what_it_bills(self):
        turn = summarise_turn(input_tokens=9035, output_tokens=3, question="hi")
        assert turn.prompt_tokens == 9035

    def test_two_calls_on_the_same_prompt_measure_the_same(self):
        cold = summarise_turn(input_tokens=9035, output_tokens=3, question="hi")
        warm = summarise_turn(
            input_tokens=5182, output_tokens=3, question="hi", cached_tokens=3853
        )
        assert cold.prompt_tokens == warm.prompt_tokens

    def test_the_billed_figure_is_still_available(self):
        turn = summarise_turn(
            input_tokens=5182, output_tokens=3, question="hi", cached_tokens=3853
        )
        assert turn.input_tokens == 5182

    def test_overhead_is_measured_against_what_was_sent(self):
        turn = summarise_turn(
            input_tokens=5182, output_tokens=3, question="hi", cached_tokens=3853
        )
        assert turn.overhead_tokens == 9035 - turn.question_tokens
