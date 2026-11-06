"""A case that only means something if the conversation got shortened.

The long-thread case asks the agent something early, buries it
under many turns, and asks about it again at the end. It is
checking that summarising the oldest turns away does not lose
what was in them.

Whether the summarising happens is not up to the case. It fires
on a fraction of the model's window, so the same case against a
larger window never triggers it — and then it passes, because
the agent simply remembered everything. A pass that means "the
conversation was short enough" reported as "compaction preserves
facts" is worse than no case at all.

So a case can say it depends on the conversation being
shortened. If it was not, the case fails and says that is why,
rather than passing on a premise that did not hold.

Deliberately a failure rather than a skip: a skip is read as
"not applicable here" and scrolls past, and this is a case that
has stopped testing what it claims to.
"""

from __future__ import annotations

from typing import Any

from agent.src.evals import lightspeed_runner as run_eval


def _group(**extra: Any) -> dict[str, Any]:
    return {
        "conversation_group_id": "long_thread_recall",
        "turns": [
            {"turn_id": "first", "query": "a", "response": "fine"},
            {"turn_id": "last", "query": "b", "response": "the answer"},
        ],
        **extra,
    }


SHORTENED = {"messages_now": 6, "most_messages": 40, "was_shortened": True}
NOT_SHORTENED = {"messages_now": 40, "most_messages": 40, "was_shortened": False}


class TestACaseThatDependsOnShortening:
    def test_it_is_left_alone_when_the_conversation_was_shortened(self):
        group = _group(requires_shortening=True)
        run_eval._enforce_shortening(group, SHORTENED)
        assert group["turns"][-1]["response"] == "the answer"

    def test_it_fails_when_the_conversation_was_not_shortened(self):
        group = _group(requires_shortening=True)
        run_eval._enforce_shortening(group, NOT_SHORTENED)
        assert group["turns"][-1]["response"] != "the answer"

    def test_the_failure_says_what_did_not_happen(self):
        # Whoever reads the report has to be able to tell this
        # from the agent getting the answer wrong. They are
        # opposite problems with opposite fixes.
        group = _group(requires_shortening=True)
        run_eval._enforce_shortening(group, NOT_SHORTENED)
        written = group["turns"][-1]["response"].lower()
        assert "shorten" in written

    def test_the_failure_says_how_long_the_conversation_got(self):
        # The fix is almost always "make the case longer" or
        # "lower the threshold", and both need the number.
        group = _group(requires_shortening=True)
        run_eval._enforce_shortening(group, NOT_SHORTENED)
        assert "40" in group["turns"][-1]["response"]

    def test_the_failure_names_the_setting_that_would_fix_it(self):
        # "Lower the threshold" is advice; naming the field is a
        # thing somebody can go and do.
        group = _group(requires_shortening=True)
        run_eval._enforce_shortening(group, NOT_SHORTENED)
        assert "trigger_fraction" in group["turns"][-1]["response"]


class TestACaseThatDoesNotDependOnIt:
    def test_an_ordinary_case_is_untouched(self):
        group = _group()
        run_eval._enforce_shortening(group, NOT_SHORTENED)
        assert group["turns"][-1]["response"] == "the answer"

    def test_even_one_that_happened_to_be_shortened(self):
        group = _group()
        run_eval._enforce_shortening(group, SHORTENED)
        assert group["turns"][-1]["response"] == "the answer"


class TestWhenTheShapeCouldNotBeRead:
    def test_it_fails_rather_than_passing_on_an_unknown(self):
        # An unreadable shape is not evidence the premise held.
        # Passing here is the same mistake one step further back.
        group = _group(requires_shortening=True)
        run_eval._enforce_shortening(group, None)
        assert group["turns"][-1]["response"] != "the answer"

    def test_it_says_it_could_not_tell(self):
        group = _group(requires_shortening=True)
        run_eval._enforce_shortening(group, None)
        assert "could not" in group["turns"][-1]["response"].lower()


class TestAGroupWithNoTurns:
    def test_it_does_not_raise(self):
        group = {
            "conversation_group_id": "empty",
            "requires_shortening": True,
            "turns": [],
        }
        run_eval._enforce_shortening(group, NOT_SHORTENED)


class TestTheShippedCaseSurvivesLoading:
    """The flag is useless if it does not reach the runner.

    It is a key the loader knows nothing about, so nothing would
    complain if a normalisation step started dropping unknown
    keys — the case would simply go back to passing for the
    wrong reason, which is the failure it exists to prevent.
    """

    def _case(self):
        from pathlib import Path

        from agent.src.evals import cases as eval_cases

        here = Path(__file__).resolve().parents[3]
        cases = eval_cases.load_cases(here / "config/agent/evals/lightspeed")
        found = [
            c
            for c in cases
            if c.get("conversation_group_id") == "long_thread_recall_after_shortening"
        ]
        assert found, "the long-thread case is not in the shipped case file"
        return found[0]

    def test_the_flag_is_still_set_after_loading(self):
        assert self._case().get("requires_shortening") is True

    def test_it_is_long_enough_to_be_worth_the_name(self):
        # A "long thread" case with four turns would never cross
        # any threshold, and the premise check would then fail
        # every run for a reason nobody could act on.
        assert len(self._case()["turns"]) >= 10

    def test_the_fact_is_stated_first_and_asked_for_last(self):
        turns = self._case()["turns"]
        assert "Lindqvist" in turns[0]["query"]
        assert "Lindqvist" not in " ".join(t["query"] for t in turns[1:-1])
        keywords = turns[-1]["expected_keywords"]
        assert any("Lindqvist" in option for group in keywords for option in group)


class TestTheRunnerUsesIt:
    """A check the run never performs is not a check."""

    def test_the_group_loop_enforces_it(self):
        import inspect

        source = inspect.getsource(run_eval._populate_group)
        assert "_enforce_shortening" in source
        assert "requires_shortening" in source

    def test_there_is_a_way_to_read_the_shape(self):
        assert callable(run_eval._fetch_thread_shape)
