"""A run that stops for approval, answered to a caller with no keyboard."""

from __future__ import annotations

from agent.src.agent.config.inbound_pause import paused_result

INTERRUPTED = {
    "__interrupt__": [
        {
            "value": {
                "action_request": {"action": "execute_sql", "args": {"q": "select 1"}},
                "description": "Run this query?",
            }
        }
    ],
    "messages": [{"type": "ai", "content": "I need to run a query."}],
}

ANSWERED = {
    "messages": [
        {"type": "human", "content": "q"},
        {"type": "ai", "content": "The limit is 750."},
    ]
}


class TestARunThatFinished:
    def test_is_not_reported_as_paused(self):
        assert paused_result(ANSWERED, thread_id="t1") is None


class TestARunThatStopped:
    def test_is_reported(self):
        assert paused_result(INTERRUPTED, thread_id="t1") is not None

    def test_says_plainly_that_it_is_not_an_answer(self):
        found = paused_result(INTERRUPTED, thread_id="t1")
        assert found["status"] == "needs_approval"

    def test_names_what_is_waiting(self):
        found = paused_result(INTERRUPTED, thread_id="t1")
        assert found["awaiting"][0]["action"] == "execute_sql"

    def test_carries_what_the_agent_wanted_to_do(self):
        found = paused_result(INTERRUPTED, thread_id="t1")
        assert "select 1" in str(found["awaiting"][0]["args"])

    def test_carries_the_reason_given(self):
        found = paused_result(INTERRUPTED, thread_id="t1")
        assert found["awaiting"][0]["description"] == "Run this query?"

    def test_says_how_to_continue_it(self):
        found = paused_result(INTERRUPTED, thread_id="t1")
        assert found["resume"]["thread_id"] == "t1"

    def test_says_what_continuing_means(self):
        found = paused_result(INTERRUPTED, thread_id="t1")
        assert set(found["resume"]["decisions"]) == {"approve", "reject"}


class TestSeveralThingsWaiting:
    def test_each_is_listed(self):
        many = {
            "__interrupt__": [
                {"value": {"action_request": {"action": "a", "args": {}}}},
                {"value": {"action_request": {"action": "b", "args": {}}}},
            ]
        }
        found = paused_result(many, thread_id="t1")
        assert [a["action"] for a in found["awaiting"]] == ["a", "b"]


class TestShapesItDoesNotRecognise:
    def test_an_interrupt_with_no_detail_is_still_reported(self):
        found = paused_result({"__interrupt__": [{}]}, thread_id="t1")
        assert found["status"] == "needs_approval"

    def test_and_says_it_could_not_name_the_action(self):
        found = paused_result({"__interrupt__": [{}]}, thread_id="t1")
        assert found["awaiting"][0]["action"] == "unknown"

    def test_an_interrupt_that_is_not_a_list_is_still_a_pause(self):
        found = paused_result({"__interrupt__": True}, thread_id="t1")
        assert found["status"] == "needs_approval"

    def test_nothing_at_all_is_not_a_pause(self):
        assert paused_result({}, thread_id="t1") is None

    def test_an_empty_interrupt_list_is_not_a_pause(self):
        assert paused_result({"__interrupt__": []}, thread_id="t1") is None


class TestItNeverLooksLikeAnAnswer:
    def test_there_is_no_answer_field(self):
        found = paused_result(INTERRUPTED, thread_id="t1")
        assert "answer" not in found

    def test_the_agents_last_words_are_not_presented_as_the_result(self):
        found = paused_result(INTERRUPTED, thread_id="t1")
        assert "750" not in str(found) and "I need to run a query" not in str(
            found.get("awaiting")
        )


REAL = {
    "interrupts": [
        {
            "value": {
                "action_requests": [
                    {
                        "name": "write_file",
                        "args": {"file_path": "/x.md", "content": "OK"},
                        "description": "write_file: Modifies files in the workspace",
                    }
                ],
                "review_configs": [
                    {
                        "action_name": "write_file",
                        "allowed_decisions": ["approve", "edit", "reject", "respond"],
                    }
                ],
            },
            "id": "e854541e",
        }
    ]
}


class TestTheShapeTheAgentActuallySends:
    """Written against a live pause, after fixtures got it wrong."""

    def test_it_is_recognised_as_a_pause(self):
        assert paused_result(REAL, thread_id="t1")["status"] == "needs_approval"

    def test_the_action_is_named(self):
        found = paused_result(REAL, thread_id="t1")
        assert found["awaiting"][0]["action"] == "write_file"

    def test_the_arguments_come_through(self):
        found = paused_result(REAL, thread_id="t1")
        assert found["awaiting"][0]["args"]["file_path"] == "/x.md"

    def test_the_description_comes_through(self):
        found = paused_result(REAL, thread_id="t1")
        assert "Modifies files" in found["awaiting"][0]["description"]

    def test_the_decisions_are_the_ones_the_agent_allows(self):
        found = paused_result(REAL, thread_id="t1")
        assert found["resume"]["decisions"] == ["approve", "edit", "reject", "respond"]

    def test_several_actions_in_one_pause_are_all_listed(self):
        many = {
            "interrupts": [
                {
                    "value": {
                        "action_requests": [
                            {"name": "a", "args": {}},
                            {"name": "b", "args": {}},
                        ]
                    }
                }
            ]
        }
        found = paused_result(many, thread_id="t1")
        assert [a["action"] for a in found["awaiting"]] == ["a", "b"]

    def test_the_older_key_still_works(self):
        assert paused_result(INTERRUPTED, thread_id="t1") is not None

    def test_without_review_configs_it_falls_back_to_the_safe_two(self):
        bare = {"interrupts": [{"value": {"action_requests": [{"name": "a"}]}}]}
        found = paused_result(bare, thread_id="t1")
        assert found["resume"]["decisions"] == ["approve", "reject"]

    def test_an_empty_interrupts_list_is_not_a_pause(self):
        assert paused_result({"interrupts": []}, thread_id="t1") is None


class TestAnInterruptItCannotParse:
    """Still a pause. Crashing here is the hang it exists to prevent."""

    def test_a_value_that_is_not_a_dictionary_does_not_raise(self):
        found = paused_result({"interrupts": [{"value": "approve?"}]}, thread_id="t1")
        assert found["status"] == "needs_approval"

    def test_it_falls_back_to_the_safe_decisions(self):
        found = paused_result({"interrupts": [{"value": "approve?"}]}, thread_id="t1")
        assert found["resume"]["decisions"] == ["approve", "reject"]

    def test_a_value_that_is_a_list_does_not_raise(self):
        found = paused_result({"interrupts": [{"value": ["x"]}]}, thread_id="t1")
        assert found["status"] == "needs_approval"

    def test_an_item_that_is_not_a_dictionary_does_not_raise(self):
        found = paused_result({"interrupts": ["stopped"]}, thread_id="t1")
        assert found["status"] == "needs_approval"
