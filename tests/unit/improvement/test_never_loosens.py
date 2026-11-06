"""A proposal that would remove a control is refused, not reviewed."""

from __future__ import annotations

import pytest

from agent.src.improvement.propose import may_propose


def _check(before, after):
    return may_propose(before=before, after=after)


class TestApprovalPolicies:
    def test_ask_to_allow_is_refused(self):
        assert not _check(
            {"human_approval.post_comment": "ask"},
            {"human_approval.post_comment": "allow"},
        ).permitted

    def test_deny_to_ask_is_refused(self):
        assert not _check(
            {"human_approval.drop_table": "deny"},
            {"human_approval.drop_table": "ask"},
        ).permitted

    def test_deny_to_allow_is_refused(self):
        assert not _check(
            {"human_approval.drop_table": "deny"},
            {"human_approval.drop_table": "allow"},
        ).permitted

    def test_allow_to_ask_is_fine(self):
        assert _check(
            {"human_approval.post_comment": "allow"},
            {"human_approval.post_comment": "ask"},
        ).permitted

    def test_removing_a_deny_rule_is_refused(self):
        assert not _check({"human_approval.drop_table": "deny"}, {}).permitted

    def test_adding_a_deny_rule_is_fine(self):
        assert _check({}, {"human_approval.drop_table": "deny"}).permitted


class TestVouchingForAServer:
    def test_adding_a_trusted_server_is_refused(self):
        assert not _check(
            {"tool_output.trusted_servers": ""},
            {"tool_output.trusted_servers": "jira"},
        ).permitted

    def test_removing_one_is_fine(self):
        assert _check(
            {"tool_output.trusted_servers": "jira"},
            {"tool_output.trusted_servers": ""},
        ).permitted

    def test_turning_fencing_off_is_refused(self):
        assert not _check(
            {"tool_output.fence": "true"}, {"tool_output.fence": "false"}
        ).permitted


class TestBudgets:
    def test_raising_a_spend_cap_is_refused(self):
        assert not _check(
            {"limits.per_person.daily_spend": "5.00"},
            {"limits.per_person.daily_spend": "50.00"},
        ).permitted

    def test_lowering_one_is_fine(self):
        assert _check(
            {"limits.per_person.daily_spend": "50.00"},
            {"limits.per_person.daily_spend": "5.00"},
        ).permitted

    def test_removing_a_cap_is_refused(self):
        assert not _check({"limits.per_person.daily_spend": "5.00"}, {}).permitted


class TestThingsItMayChange:
    def test_a_prompt_may_be_rewritten(self):
        assert _check({"prompt": "old wording"}, {"prompt": "new wording"}).permitted

    def test_a_tool_description_may_change(self):
        assert _check(
            {"tools.ask.description": "a"}, {"tools.ask.description": "b"}
        ).permitted

    def test_a_retrieval_setting_may_move_either_way(self):
        assert _check(
            {"knowledge.retrieval.top_k": "8"}, {"knowledge.retrieval.top_k": "20"}
        ).permitted

    def test_nothing_changed_is_permitted(self):
        assert _check({"prompt": "same"}, {"prompt": "same"}).permitted


class TestConfigurationAsItIsActuallyWritten:
    """Nested sections, and the words `agent.yaml` uses."""

    def test_a_cap_raised_inside_a_section_is_refused(self):
        found = _check(
            {"limits": {"per_person": {"daily_spend": "5.00"}}},
            {"limits": {"per_person": {"daily_spend": "500.00"}}},
        )
        assert not found.permitted
        assert "limits.per_person.daily_spend" in found.reason

    def test_a_prompt_edit_beside_an_untouched_control_is_permitted(self):
        control = {"enabled": True, "mode": "all", "exclude": ["write_todos"]}
        assert _check(
            {"human_approval": dict(control), "prompt": "a"},
            {"human_approval": dict(control), "prompt": "b"},
        ).permitted

    def test_turning_approval_off_is_refused(self):
        found = _check(
            {"human_approval": {"enabled": True}},
            {"human_approval": {"enabled": False}},
        )
        assert not found.permitted
        assert "turns tool approval off" in found.reason

    def test_turning_it_on_is_fine(self):
        assert _check(
            {"human_approval": {"enabled": False}},
            {"human_approval": {"enabled": True}},
        ).permitted

    def test_mode_all_to_none_is_refused_in_those_words(self):
        found = _check(
            {"human_approval": {"mode": "all"}},
            {"human_approval": {"mode": "none"}},
        )
        assert not found.permitted
        assert "widens all to none" in found.reason

    def test_narrowing_the_mode_is_fine(self):
        assert _check(
            {"human_approval": {"mode": "none"}},
            {"human_approval": {"mode": "all"}},
        ).permitted

    def test_excusing_one_more_tool_from_approval_is_refused(self):
        found = _check(
            {"human_approval": {"exclude": ["write_todos"]}},
            {"human_approval": {"exclude": ["write_todos", "write_file"]}},
        )
        assert not found.permitted
        assert "write_file" in found.reason

    def test_shortening_the_exclusions_is_fine(self):
        assert _check(
            {"human_approval": {"exclude": ["write_todos", "write_file"]}},
            {"human_approval": {"exclude": ["write_todos"]}},
        ).permitted

    def test_removing_the_whole_section_is_refused(self):
        assert not _check(
            {"human_approval": {"enabled": True, "mode": "all"}},
            {},
        ).permitted

    def test_a_nested_prompt_may_still_be_rewritten(self):
        assert _check(
            {"agent": {"prompt": {"system": "a"}}},
            {"agent": {"prompt": {"system": "b"}}},
        ).permitted


class TestTheRefusalIsUsable:
    def test_it_names_the_setting(self):
        found = _check(
            {"human_approval.post_comment": "ask"},
            {"human_approval.post_comment": "allow"},
        )
        assert "post_comment" in found.reason

    def test_it_names_the_direction(self):
        found = _check(
            {"human_approval.post_comment": "ask"},
            {"human_approval.post_comment": "allow"},
        )
        assert "ask" in found.reason and "allow" in found.reason

    def test_several_loosenings_are_all_named(self):
        found = _check(
            {
                "human_approval.a": "ask",
                "limits.per_person.daily_spend": "5.00",
            },
            {
                "human_approval.a": "allow",
                "limits.per_person.daily_spend": "50.00",
            },
        )
        assert "human_approval.a" in found.reason
        assert "daily_spend" in found.reason

    def test_a_permitted_proposal_needs_no_reason(self):
        assert _check({"prompt": "a"}, {"prompt": "b"}).reason == ""


class TestItFailsClosed:
    def test_a_setting_it_cannot_judge_is_left_alone(self):
        assert _check({"something.odd": "a"}, {"something.odd": "b"}).permitted

    def test_an_unreadable_amount_on_a_cap_is_refused(self):
        assert not _check(
            {"limits.per_person.daily_spend": "5.00"},
            {"limits.per_person.daily_spend": "lots"},
        ).permitted

    @pytest.mark.parametrize("bad", [None, "not a mapping", 7])
    def test_something_that_is_not_a_configuration_is_refused(self, bad):
        assert not may_propose(before=bad, after={"prompt": "x"}).permitted


class TestItIsReachable:
    """A gate nothing calls stops nothing."""

    def test_the_command_line_can_ask(self):
        from agent.cli.main import main

        assert main is not None

    def test_a_loosening_is_refused_from_the_command_line(self, capsys, tmp_path):
        import json

        from agent.cli.main import main

        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        before.write_text(json.dumps({"human_approval.post_comment": "ask"}))
        after.write_text(json.dumps({"human_approval.post_comment": "allow"}))

        code = main(["propose", "--before", str(before), "--after", str(after)])
        said = capsys.readouterr().out
        assert code != 0
        assert "post_comment" in said

    def test_a_safe_change_is_allowed_from_the_command_line(self, capsys, tmp_path):
        import json

        from agent.cli.main import main

        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        before.write_text(json.dumps({"prompt": "old"}))
        after.write_text(json.dumps({"prompt": "new"}))

        assert main(["propose", "--before", str(before), "--after", str(after)]) == 0

    def test_a_file_that_is_not_there_is_said_plainly(self, capsys, tmp_path):
        from agent.cli.main import main

        code = main(
            [
                "propose",
                "--before",
                str(tmp_path / "no.json"),
                "--after",
                str(tmp_path / "no.json"),
            ]
        )
        assert code != 0
        assert "no.json" in capsys.readouterr().err

    def test_a_refusal_does_not_go_to_the_answer_stream_as_an_error(
        self, capsys, tmp_path
    ):
        import json

        from agent.cli.main import main

        before = tmp_path / "b.json"
        after = tmp_path / "a.json"
        before.write_text(json.dumps({"human_approval.x": "deny"}))
        after.write_text(json.dumps({"human_approval.x": "allow"}))

        main(["propose", "--before", str(before), "--after", str(after)])
        captured = capsys.readouterr()
        assert "human_approval.x" in captured.out
        assert captured.err == ""
