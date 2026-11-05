"""An observation becomes a diff, or says why it cannot (E12-T3)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from agent.src.improvement.generate import MIN_SEEN, generate

CONFIG = """\
middleware:
  model_call_limit:
    enabled: true
    run_limit: 250
  # Tools removed by product decision.
  tool_exclusion:
    enabled: true
    tools:
      - dataverse_get_sql
      - dataverse_shortlist_tables

  tool_call_limit:
    enabled: true
"""


@dataclass
class Seen:
    kind: str
    detail: str
    seen: int = MIN_SEEN
    runs: list[str] = field(default_factory=lambda: ["run-1"])
    run_id: str = "run-1"
    last_seen: str | None = None


def _one(kind, detail, seen=MIN_SEEN, config=CONFIG):
    made = generate([Seen(kind, detail, seen)], config_text=config)
    return made[0] if made else None


class TestAToolNobodyUses:
    def test_it_is_proposed_for_exclusion(self):
        found = _one("tool_abandoned", "web_search was called and its result unused")
        assert found.permitted
        assert "+      - web_search" in found.diff

    def test_nothing_else_in_the_file_moves(self):
        found = _one("tool_abandoned", "web_search was called and its result unused")
        body = found.diff.splitlines()[2:]
        assert [line for line in body if line.startswith("+")] == [
            "+      - web_search"
        ]
        assert not [line for line in body if line.startswith("-")]

    def test_the_argument_names_how_often(self):
        found = _one(
            "tool_abandoned", "web_search was called and its result unused", seen=7
        )
        assert "7 run(s)" in found.argument

    def test_once_is_not_a_pattern(self):
        assert _one("tool_abandoned", "web_search was unused", seen=1) is None

    def test_a_tool_already_excluded_gets_no_diff(self):
        found = _one("tool_abandoned", "dataverse_get_sql was called and unused")
        assert found.diff == ""
        assert "already excluded" in found.blocked

    def test_a_configuration_with_no_such_list_is_said_plainly(self):
        found = _one(
            "tool_abandoned",
            "web_search was called and unused",
            config="middleware:\n  memory:\n    enabled: true\n",
        )
        assert found.diff == ""
        assert found.blocked


class TestTheSignalThisLoopMayNotActOn:
    def test_raising_the_call_limit_is_refused(self):
        found = _one("budget_spent", "ran out of calls for: research")
        assert not found.permitted
        assert "run_limit" in found.refusal
        assert found.diff == ""

    def test_the_argument_still_explains_the_observation(self):
        found = _one("budget_spent", "ran out of calls for: research")
        assert "250" in found.argument

    def test_a_configuration_with_no_limit_gets_no_proposal(self):
        found = _one(
            "budget_spent", "ran out of calls", config="middleware:\n  memory: {}\n"
        )
        assert found.diff == ""
        assert "no model call limit" in found.blocked


class TestWhatItWillNotWrite:
    @pytest.mark.parametrize("kind", ["repeated_question", "empty_delegation"])
    def test_a_prompt_fix_is_declined_with_its_reason(self, kind):
        found = _one(kind, "something happened")
        assert found.diff == ""
        assert "write words" in found.blocked

    def test_an_unknown_observation_produces_nothing(self):
        assert generate([Seen("something_new", "x")], config_text=CONFIG) == []


class TestItIsBounded:
    def test_no_more_than_asked_for(self):
        many = [
            Seen("tool_abandoned", f"tool_{i} was called and its result unused")
            for i in range(20)
        ]
        assert len(generate(many, config_text=CONFIG, max_per_run=3)) == 3


class TestEveryProposalPassesTheControlCheck:
    def test_the_verdict_is_recorded_either_way(self, monkeypatch):
        seen = []
        import agent.src.audit as audit

        monkeypatch.setattr(
            audit, "emit_audit_event", lambda kind, **rest: seen.append(rest)
        )
        generate(
            [
                Seen("tool_abandoned", "web_search was called and its result unused"),
                Seen("budget_spent", "ran out of calls"),
            ],
            config_text=CONFIG,
        )
        assert [one["permitted"] for one in seen] == [True, False]
        assert all(one["source"] == "improvement.generate" for one in seen)


class TestAnObservationCanBeTooOld:
    """Traces do not know which build produced them."""

    def _old(self, last_seen):
        one = Seen("tool_abandoned", "web_search was called and its result unused")
        one.last_seen = last_seen
        return one

    def test_something_last_seen_months_ago_gets_no_diff(self):
        found = generate([self._old("2026-01-01T00:00:00Z")], config_text=CONFIG)[0]
        assert found.diff == ""
        assert "more than 14 days ago" in found.blocked

    def test_something_recent_still_does(self):
        from datetime import datetime, timedelta, timezone

        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        assert generate([self._old(recent)], config_text=CONFIG)[0].diff

    def test_an_undated_observation_is_not_treated_as_old(self):
        assert generate([self._old(None)], config_text=CONFIG)[0].diff

    def test_the_window_can_be_turned_off(self):
        found = generate(
            [self._old("2026-01-01T00:00:00Z")],
            config_text=CONFIG,
            stale_after_days=0,
        )[0]
        assert found.diff
