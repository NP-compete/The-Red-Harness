"""Answer notes travelling with the message that earned them."""

from __future__ import annotations

from types import SimpleNamespace

from agent.aegra.provenance import describe_message


def _msg(extra=None):
    return SimpleNamespace(
        response_metadata={},
        additional_kwargs=extra or {},
        content="The limit is 750 euros.",
        tool_calls=None,
        type="ai",
    )


def _notes(unsupported, checked=1, stance="plain", concerns=()):
    return {
        "answer_notes": {
            "figures": {"checked": checked, "unsupported": unsupported},
            "stance": stance,
            "hedge": "; ".join(concerns),
            "concerns": list(concerns),
        }
    }


def test_a_hedged_answer_reaches_the_reader():
    described = describe_message(
        _msg(_notes([], stance="hedged", concerns=("this rests on a single source",)))
    )
    assert described["answer_notes"]["stance"] == "hedged"


def test_what_is_shaky_reaches_the_reader():
    described = describe_message(
        _msg(_notes([], stance="hedged", concerns=("this rests on a single source",)))
    )
    assert described["answer_notes"]["concerns"] == ["this rests on a single source"]


def test_an_answer_the_turn_could_not_stand_behind_reaches_the_reader():
    described = describe_message(_msg(_notes([], stance="decline", concerns=("x",))))
    assert described["answer_notes"]["stance"] == "decline"


def test_a_plain_answer_with_clean_figures_says_nothing():
    assert "answer_notes" not in describe_message(_msg(_notes([])))


def _looped(pattern="repeating"):
    notes = _notes([])
    notes["answer_notes"]["loop"] = {
        "pattern": pattern,
        "should_stop": True,
        "repeated": "search",
        "times": 3,
        "reason": "search ran 3 times with the same arguments",
    }
    return notes


def test_a_turn_that_went_round_in_circles_reaches_the_reader():
    described = describe_message(_msg(_looped()))
    assert described["answer_notes"]["loop"]["pattern"] == "repeating"


def test_the_repeated_tool_reaches_the_reader():
    described = describe_message(_msg(_looped()))
    assert described["answer_notes"]["loop"]["repeated"] == "search"


def test_a_flagged_figure_reaches_the_reader():
    described = describe_message(_msg(_notes(["750"])))
    assert described["answer_notes"]["figures"]["unsupported"] == ["750"]


def test_how_many_figures_were_checked_reaches_the_reader():
    described = describe_message(_msg(_notes(["750"], checked=2)))
    assert described["answer_notes"]["figures"]["checked"] == 2


def test_an_answer_whose_figures_all_check_out_says_nothing():
    assert "answer_notes" not in describe_message(_msg(_notes([])))


def test_a_message_with_no_notes_says_nothing():
    assert "answer_notes" not in describe_message(_msg())


def test_notes_that_are_not_a_dict_are_ignored():
    assert "answer_notes" not in describe_message(_msg({"answer_notes": "yes"}))


def test_the_rest_of_the_provenance_still_comes_through():
    described = describe_message(_msg({**_notes(["750"]), "routed_tier": "fast"}))
    assert described["routed_tier"] == "fast"


def test_an_unanswered_part_of_the_question_reaches_the_reader():
    notes = _notes([])
    notes["answer_notes"]["coverage"] = {
        "complete": False,
        "uncovered": ["Also when must receipts be filed"],
        "unused": [],
        "share": 0.5,
        "part_count": 2,
    }
    described = describe_message(_msg(notes))
    assert described["answer_notes"]["coverage"]["uncovered"] == [
        "Also when must receipts be filed"
    ]


def test_a_fully_covered_question_says_nothing():
    notes = _notes([])
    notes["answer_notes"]["coverage"] = {
        "complete": True,
        "uncovered": [],
        "unused": [],
        "share": 1.0,
        "part_count": 1,
    }
    assert "answer_notes" not in describe_message(_msg(notes))


def test_a_sentence_resting_on_nothing_reaches_the_reader():
    notes = _notes([])
    notes["answer_notes"]["claims"] = [
        {
            "text": "Reimbursement needs a signature.",
            "supported": False,
            "contradicted": False,
        }
    ]
    described = describe_message(_msg(notes))
    assert (
        described["answer_notes"]["claims"][0]["text"]
        == "Reimbursement needs a signature."
    )


def test_an_answer_whose_sentences_all_check_out_says_nothing():
    notes = _notes([])
    notes["answer_notes"]["claims"] = []
    assert "answer_notes" not in describe_message(_msg(notes))


def test_planted_instructions_reach_the_reader():
    notes = {
        "answer_notes": {
            "figures": {"checked": 0, "unsupported": []},
            "stance": "plain",
            "injection": {
                "signals": ["override-attempt"],
                "evidence": ["Ignore all previous instructions"],
            },
        }
    }
    described = describe_message(_msg(notes))
    assert described["answer_notes"]["injection"]["signals"] == ["override-attempt"]


class TestAWithheldToolReachesTheReader:
    """A clean turn says nothing; a tool taken away is worth a line."""

    @staticmethod
    def _with_budget(budget):
        notes = {
            "answer_notes": {
                "figures": {"checked": 1, "unsupported": []},
                "stance": "plain",
                "hedge": "",
                "concerns": [],
                "budget": budget,
            }
        }
        return describe_message(_msg(notes))

    def test_an_otherwise_clean_turn_still_carries_it(self):
        described = self._with_budget(
            {"withheld": ["grep"], "scope": "block", "limit": 3}
        )
        assert described["answer_notes"]["budget"]["withheld"] == ["grep"]

    def test_the_scope_travels_with_it(self):
        described = self._with_budget(
            {"withheld": ["grep"], "scope": "conversation", "limit": 5}
        )
        assert described["answer_notes"]["budget"]["scope"] == "conversation"

    def test_a_clean_turn_with_no_budget_note_says_nothing(self):
        assert "answer_notes" not in describe_message(_msg(_notes([])))
