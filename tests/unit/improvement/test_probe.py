"""A proposal weighed against the runs behind it (E12-T4)."""

from __future__ import annotations

from dataclasses import dataclass

from agent.src.improvement.probe import probe, tool_withdrawn_by


@dataclass
class FakeProposal:
    diff: str


def _diff(tool):
    return f"--- a/x\n+++ b/x\n@@ -1 +1,2 @@\n       - other\n+      - {tool}\n"


def _run(run_id, result, after):
    return {
        "run_id": run_id,
        "messages": [
            {"type": "human", "content": "q"},
            {"type": "ai", "content": "", "tool_calls": [{"name": "sql", "id": "c"}]},
            {"type": "tool", "tool_call_id": "c", "name": "sql", "content": result},
            {"type": "ai", "content": after},
        ],
    }


class TestReadingTheDiff:
    def test_it_finds_the_tool_being_withdrawn(self):
        assert tool_withdrawn_by(_diff("sql")) == "sql"

    def test_a_diff_it_cannot_read_probes_nothing(self):
        assert probe(FakeProposal("--- a/x\n+++ b/x\n+something: else\n"), []) is None

    def test_nor_does_a_diff_touching_two_entries(self):
        assert tool_withdrawn_by(_diff("a") + "+      - b\n") == ""


class TestWhatItWouldHaveCost:
    def test_calls_that_fed_an_answer_make_it_a_refusal(self):
        found = probe(
            FakeProposal(_diff("sql")),
            [_run("r1", "42 rows in orders", "There are 42 rows in orders.")],
        )
        assert found.touched == 1 and found.used == 1
        assert "refuse" in found.verdict

    def test_calls_nothing_drew_on_cost_nothing_visible(self):
        found = probe(
            FakeProposal(_diff("sql")),
            [_run("r1", "42 rows in orders", "I cannot answer that.")],
        )
        assert found.used == 0
        assert "costs nothing visible" in found.verdict

    def test_it_counts_across_every_run_and_names_them(self):
        found = probe(
            FakeProposal(_diff("sql")),
            [
                _run("r1", "alpha beta gamma", "alpha beta gamma"),
                _run("r2", "alpha beta gamma", "no idea"),
            ],
        )
        assert (found.touched, found.used) == (2, 1)
        assert found.runs == ["r1", "r2"]

    def test_finding_no_calls_is_reported_as_a_disagreement(self):
        found = probe(FakeProposal(_diff("web_search")), [_run("r1", "x y z", "q")])
        assert found.touched == 0
        assert "disagrees with the observation" in found.verdict


class TestItDoesNotPretendToHaveRunAnything:
    def test_rerun_is_false_and_part_of_the_payload(self):
        found = probe(FakeProposal(_diff("sql")), [_run("r1", "a b c", "a b c")])
        assert found.rerun is False
