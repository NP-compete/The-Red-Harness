"""Signals in a run that configuration could fix."""

from __future__ import annotations

from agent.src.improvement.mine import mine

RUN = {
    "run_id": "r1",
    "thread_id": "t1",
    "messages": [
        {"type": "human", "content": "what is the travel limit?"},
        {"type": "ai", "content": "The limit is 750."},
    ],
}


def _names(found):
    return [o.kind for o in found]


class TestAnOrdinaryRun:
    def test_has_nothing_to_observe(self):
        assert mine([RUN]) == []


class TestAToolCalledAndAbandoned:
    """Asked for, came back, and never referred to again."""

    abandoned = {
        **RUN,
        "messages": [
            {"type": "human", "content": "q"},
            {
                "type": "ai",
                "content": "",
                "tool_calls": [{"name": "execute_sql", "id": "c1"}],
            },
            {
                "type": "tool",
                "tool_call_id": "c1",
                "name": "execute_sql",
                "content": "42 rows",
            },
            {"type": "ai", "content": "I cannot answer that."},
        ],
    }

    def test_it_is_observed(self):
        assert "tool_abandoned" in _names(mine([self.abandoned]))

    def test_it_names_the_tool(self):
        found = [o for o in mine([self.abandoned]) if o.kind == "tool_abandoned"]
        assert "execute_sql" in found[0].detail

    def test_it_names_the_run_so_somebody_can_look(self):
        found = mine([self.abandoned])
        assert found[0].run_id == "r1"

    def test_a_tool_whose_result_was_used_is_not_observed(self):
        used = {
            **RUN,
            "messages": [
                {
                    "type": "ai",
                    "content": "",
                    "tool_calls": [{"name": "sql", "id": "c1"}],
                },
                {
                    "type": "tool",
                    "tool_call_id": "c1",
                    "name": "sql",
                    "content": "42 rows",
                },
                {"type": "ai", "content": "There are 42 rows."},
            ],
        }
        assert "tool_abandoned" not in _names(mine([used]))


class TestWhatAbandonedDoesNotMean:
    """Three things this used to report as an unused result."""

    def _run(self, result, after="I cannot answer that."):
        return {
            **RUN,
            "messages": [
                {"type": "human", "content": "q"},
                {
                    "type": "ai",
                    "content": "",
                    "tool_calls": [{"name": "ls", "id": "c1"}],
                },
                {"type": "tool", "tool_call_id": "c1", "name": "ls", "content": result},
                {"type": "ai", "content": after},
            ],
        }

    def test_a_tool_that_errored_is_its_own_observation(self):
        found = _names(mine([self._run("Error: Path '/': path_not_found")]))
        assert "tool_failed" in found
        assert "tool_abandoned" not in found

    def test_a_search_that_found_nothing_is_not_an_observation(self):
        assert _names(mine([self._run("No files found")])) == []

    def test_but_a_document_mentioning_not_found_still_counts(self):
        long_result = "The rates table lists every tier. " * 4 + "not found"
        assert "tool_abandoned" in _names(mine([self._run(long_result)]))

    def test_a_run_that_stopped_after_the_tool_is_not_an_unused_result(self):
        found = _names(mine([self._run("alpha beta gamma delta", after=[])]))
        assert "answer_missing" in found
        assert "tool_abandoned" not in found

    def test_a_write_that_only_confirmed_itself_is_not_an_observation(self):
        assert (
            _names(mine([self._run("Successfully replaced 1 instance(s)", after="OK")]))
            == []
        )

    def test_a_one_word_number_counts_as_using_the_result(self):
        found = _names(
            mine([self._run("The sabbatical policy allows 8 weeks", after="8")])
        )
        assert "tool_abandoned" not in found

    def test_an_answer_in_content_blocks_is_read_as_words(self):
        after = [{"type": "text", "text": "There are alpha beta gamma here."}]
        assert "tool_abandoned" not in _names(
            mine([self._run("alpha beta gamma delta", after=after)])
        )


class TestASubagentThatReturnedNothing:
    empty = {
        **RUN,
        "messages": [
            {"type": "ai", "content": "", "tool_calls": [{"name": "task", "id": "c1"}]},
            {"type": "tool", "tool_call_id": "c1", "name": "task", "content": "   "},
            {"type": "ai", "content": "I could not find anything."},
        ],
    }

    def test_it_is_observed(self):
        assert "empty_delegation" in _names(mine([self.empty]))

    def test_it_is_not_also_called_an_abandoned_tool(self):
        assert _names(mine([self.empty])).count("tool_abandoned") == 0


class TestARunThatHitACeiling:
    capped = {
        **RUN,
        "messages": [
            {
                "type": "system",
                "content": "The call budget for this block is spent for: ls",
            },
            {"type": "ai", "content": "Answering from what I have."},
        ],
    }

    def test_it_is_observed(self):
        assert "budget_spent" in _names(mine([self.capped]))

    def test_it_says_what_ran_out(self):
        found = [o for o in mine([self.capped]) if o.kind == "budget_spent"]
        assert "ls" in found[0].detail


class TestTheSameQuestionAskedAgain:
    repeated = {
        **RUN,
        "messages": [
            {"type": "human", "content": "what is the limit?"},
            {"type": "ai", "content": "Which country did you mean?"},
            {"type": "human", "content": "france"},
            {"type": "ai", "content": "Which country did you mean?"},
        ],
    }

    def test_it_is_observed(self):
        assert "repeated_question" in _names(mine([self.repeated]))


class TestRanking:
    def test_the_most_frequent_observation_comes_first(self):
        runs = [TestAToolCalledAndAbandoned.abandoned] * 3 + [
            TestARunThatHitACeiling.capped
        ]
        assert _names(mine(runs))[0] == "tool_abandoned"

    def test_each_kind_is_reported_once_with_a_count(self):
        runs = [TestAToolCalledAndAbandoned.abandoned] * 3
        found = mine(runs)
        assert len(found) == 1 and found[0].seen == 3

    def test_every_run_it_came_from_is_listed(self):
        runs = [
            {**TestAToolCalledAndAbandoned.abandoned, "run_id": "r1"},
            {**TestAToolCalledAndAbandoned.abandoned, "run_id": "r2"},
        ]
        assert mine(runs)[0].runs == ["r1", "r2"]


class TestItProposesNothing:
    """Evidence, not an argument. A list that arrives already"""

    def test_an_observation_carries_no_suggested_change(self):
        found = mine([TestAToolCalledAndAbandoned.abandoned])[0]
        assert not hasattr(found, "suggestion")

    def test_nor_a_diff(self):
        found = mine([TestAToolCalledAndAbandoned.abandoned])[0]
        assert not hasattr(found, "diff")


class TestWhatItWillNotCrashOn:
    def test_a_run_with_no_messages(self):
        assert mine([{"run_id": "r1", "messages": []}]) == []

    def test_a_run_that_is_not_a_run(self):
        assert mine(["not a run"]) == []

    def test_nothing_at_all(self):
        assert mine([]) == []


class TestWhenItHappened:
    """An old observation is not evidence about today's build."""

    @staticmethod
    def _run(at, run_id="r1"):
        return {
            **TestAToolCalledAndAbandoned.abandoned,
            "run_id": run_id,
            "created_at": at,
        }

    def test_an_observation_says_when_it_was_last_seen(self):
        found = mine([self._run("2026-10-27T14:28:23Z")])
        assert found[0].last_seen == "2026-10-27T14:28:23Z"

    def test_the_most_recent_sighting_is_the_one_reported(self):
        found = mine(
            [
                self._run("2026-10-20T10:00:00Z", "r1"),
                self._run("2026-10-28T10:00:00Z", "r2"),
            ]
        )
        assert found[0].last_seen == "2026-10-28T10:00:00Z"

    def test_a_run_with_no_date_does_not_invent_one(self):
        found = mine([TestAToolCalledAndAbandoned.abandoned])
        assert found[0].last_seen is None

    def test_runs_before_the_window_are_not_mined(self):
        found = mine([self._run("2026-10-20T10:00:00Z")], since="2026-10-27T00:00:00Z")
        assert found == []

    def test_runs_inside_the_window_are(self):
        found = mine([self._run("2026-10-28T10:00:00Z")], since="2026-10-27T00:00:00Z")
        assert len(found) == 1

    def test_a_run_with_no_date_is_kept_rather_than_guessed_about(self):
        found = mine(
            [TestAToolCalledAndAbandoned.abandoned], since="2026-10-27T00:00:00Z"
        )
        assert len(found) == 1

    def test_an_unreadable_date_is_treated_the_same_way(self):
        found = mine(
            [self._run("the day before yesterday")], since="2026-10-27T00:00:00Z"
        )
        assert len(found) == 1

    def test_without_a_window_everything_is_mined(self):
        found = mine([self._run("2020-01-01T00:00:00Z")])
        assert len(found) == 1


class TestASkillLoadedAndNotUsed:
    """E12-T2.1. A skill is instructions for doing something."""

    def _run(self, *, acted: bool, path="/skills/dataverse/SKILL.md"):
        messages = [
            {"type": "human", "content": "q"},
            {
                "type": "ai",
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "id": "s1", "args": {"file_path": path}}
                ],
            },
            {
                "type": "tool",
                "tool_call_id": "s1",
                "name": "read_file",
                "content": "do this",
            },
        ]
        if acted:
            messages += [
                {
                    "type": "ai",
                    "content": "",
                    "tool_calls": [
                        {"name": "sql", "id": "c1", "args": {"q": "select 1"}}
                    ],
                },
                {
                    "type": "tool",
                    "tool_call_id": "c1",
                    "name": "sql",
                    "content": "1 row",
                },
            ]
        messages.append({"type": "ai", "content": "here you go"})
        return {**RUN, "messages": messages}

    def test_reading_one_and_doing_nothing_is_observed(self):
        found = mine([self._run(acted=False)])
        assert "skill_unused" in _names(found)

    def test_the_skill_is_named(self):
        found = [o for o in mine([self._run(acted=False)]) if o.kind == "skill_unused"]
        assert "dataverse" in found[0].detail

    def test_acting_on_it_is_not_observed(self):
        assert "skill_unused" not in _names(mine([self._run(acted=True)]))

    def test_reading_two_and_acting_on_the_second_is_not_observed(self):
        run = self._run(acted=True)
        run["messages"][1:1] = [
            {
                "type": "ai",
                "content": "",
                "tool_calls": [
                    {
                        "name": "read_file",
                        "id": "s0",
                        "args": {"file_path": "/skills/other/SKILL.md"},
                    }
                ],
            },
            {
                "type": "tool",
                "tool_call_id": "s0",
                "name": "read_file",
                "content": "or this",
            },
        ]
        assert "skill_unused" not in _names(mine([run]))

    def test_an_ordinary_file_is_not_a_skill(self):
        assert "skill_unused" not in _names(
            mine([self._run(acted=False, path="/documents/rates.md")])
        )

    def test_a_grep_pattern_is_not_read_as_the_skill_name(self):
        run = self._run(acted=False)
        run["messages"][1]["tool_calls"] = [
            {
                "name": "grep",
                "id": "s1",
                "args": {
                    "path": "/skills/dataverse/references",
                    "pattern": "travel\nand more",
                },
            }
        ]
        found = [o for o in mine([run]) if o.kind == "skill_unused"]
        assert found[0].detail == "the dataverse skill was read and nothing followed it"
