"""Running one benchmark task against this agent."""

from __future__ import annotations

import pytest

from scripts.bench.executor import AgentExecutor


class _Transport:
    """Enough of the run API to see what the adapter did to it."""

    def __init__(self, *, reply=None, status=200, fail_on=None):
        self.reply = (
            reply
            if reply is not None
            else {"messages": [{"type": "ai", "content": "The answer is 42."}]}
        )
        self.status = status
        self.fail_on = fail_on or ""
        self.calls: list[tuple[str, str]] = []

    def post(self, path, body=None, timeout=None):
        self.calls.append(("POST", path))
        if self.fail_on and self.fail_on in path:
            raise TimeoutError("took too long")
        if path == "/threads":
            return 200, {"thread_id": "t1"}
        return self.status, self.reply

    def delete(self, path):
        self.calls.append(("DELETE", path))
        return 200, {}


def _ran(tmp_path, transport, **kwargs):
    return AgentExecutor(transport=transport).run(
        cwd=tmp_path, mission=kwargs.pop("mission", "Add 17 and 25."), **kwargs
    )


class TestOneTask:
    def test_it_gets_its_own_conversation(self, tmp_path):
        transport = _Transport()
        _ran(tmp_path, transport)
        assert ("POST", "/threads") in transport.calls

    def test_the_mission_is_what_is_asked(self, tmp_path):
        transport = _Transport()
        _ran(tmp_path, transport)
        assert ("POST", "/threads/t1/runs/wait") in transport.calls

    def test_the_answer_comes_back(self, tmp_path):
        assert _ran(tmp_path, _Transport()).text == "The answer is 42."

    def test_a_good_attempt_reports_no_error(self, tmp_path):
        assert _ran(tmp_path, _Transport()).error == ""


class TestWhereTheAnswerGoes:
    def test_it_is_written_to_the_file_the_runner_reads(self, tmp_path):
        _ran(tmp_path, _Transport())
        assert (tmp_path / "output" / "answer.md").read_text() == "The answer is 42."

    def test_the_directory_is_made_if_it_is_not_there(self, tmp_path):
        _ran(tmp_path, _Transport())
        assert (tmp_path / "output").is_dir()

    def test_the_mission_is_left_where_the_task_can_see_it(self, tmp_path):
        _ran(tmp_path, _Transport(), mission="Add 17 and 25.")
        assert "Add 17 and 25." in (tmp_path / "MISSION.md").read_text()

    def test_a_system_instruction_sits_above_the_mission(self, tmp_path):
        _ran(tmp_path, _Transport(), mission="Do it.", system="Be brief.")
        said = (tmp_path / "MISSION.md").read_text()
        assert said.index("Be brief.") < said.index("Do it.")

    def test_no_system_instruction_leaves_no_separator(self, tmp_path):
        _ran(tmp_path, _Transport(), mission="Do it.")
        assert (tmp_path / "MISSION.md").read_text().strip() == "Do it."


class TestAnEmptyAnswer:
    def test_it_is_an_error_rather_than_a_score_of_zero(self, tmp_path):
        transport = _Transport(reply={"messages": []})
        assert _ran(tmp_path, transport).error

    def test_the_text_is_empty_too(self, tmp_path):
        transport = _Transport(reply={"messages": []})
        assert _ran(tmp_path, transport).text == ""

    def test_nothing_is_written_to_the_answer_file(self, tmp_path):
        transport = _Transport(reply={"messages": []})
        _ran(tmp_path, transport)
        assert not (tmp_path / "output" / "answer.md").exists()


class TestNoConversationIsLeftBehind:
    """A suite is thousands of these."""

    def test_a_finished_task_cleans_up_after_itself(self, tmp_path):
        transport = _Transport()
        _ran(tmp_path, transport)
        assert ("DELETE", "/threads/t1") in transport.calls

    def test_a_failed_task_cleans_up_too(self, tmp_path):
        transport = _Transport(status=500, reply={"detail": "boom"})
        _ran(tmp_path, transport)
        assert ("DELETE", "/threads/t1") in transport.calls

    def test_a_task_that_timed_out_cleans_up_too(self, tmp_path):
        transport = _Transport(fail_on="runs/wait")
        _ran(tmp_path, transport)
        assert ("DELETE", "/threads/t1") in transport.calls

    def test_cleanup_that_fails_does_not_lose_the_answer(self, tmp_path):
        class _Stuck(_Transport):
            def delete(self, path):
                raise ConnectionError("gone")

        assert _ran(tmp_path, _Stuck()).text == "The answer is 42."


class TestATaskThatRanOutOfTime:
    def test_it_is_reported_as_an_error(self, tmp_path):
        transport = _Transport(fail_on="runs/wait")
        assert _ran(tmp_path, transport).error

    def test_the_error_says_it_was_the_time(self, tmp_path):
        transport = _Transport(fail_on="runs/wait")
        assert "time" in _ran(tmp_path, transport).error.lower()

    def test_the_run_is_cancelled_rather_than_abandoned(self, tmp_path):
        transport = _Transport(fail_on="runs/wait")
        _ran(tmp_path, transport)
        assert any("cancel" in path for _, path in transport.calls)

    def test_the_wall_is_passed_to_the_request(self, tmp_path):
        seen = {}

        class _Timed(_Transport):
            def post(self, path, body=None, timeout=None):
                seen[path] = timeout
                return super().post(path, body, timeout)

        _ran(tmp_path, _Timed(), wall=30)
        assert seen["/threads/t1/runs/wait"] == 30


class TestWhatATaskIsNotToldToDo:
    def test_it_does_not_score_itself(self, tmp_path):
        found = _ran(tmp_path, _Transport())
        assert not hasattr(found, "score")

    def test_the_cost_is_reported_as_unknown_rather_than_guessed(self, tmp_path):
        assert _ran(tmp_path, _Transport()).cost == 0.0


class TestARunThatFailedInsideASuccess:
    def test_it_is_an_error(self, tmp_path):
        transport = _Transport(reply={"__error__": {"message": "execution failed"}})
        assert _ran(tmp_path, transport).error

    def test_the_reason_is_carried_through(self, tmp_path):
        transport = _Transport(reply={"__error__": {"message": "execution failed"}})
        assert "execution failed" in _ran(tmp_path, transport).error


class TestARunThatStoppedForADecision:
    def test_it_is_an_error_rather_than_a_blank(self, tmp_path):
        paused = {
            "interrupts": [{"value": {"action_requests": [{"name": "write_file"}]}}]
        }
        assert _ran(tmp_path, _Transport(reply=paused)).error

    def test_the_error_says_what_it_was_waiting_for(self, tmp_path):
        paused = {
            "interrupts": [{"value": {"action_requests": [{"name": "write_file"}]}}]
        }
        assert "write_file" in _ran(tmp_path, _Transport(reply=paused)).error


@pytest.mark.parametrize("wall", [0, -1])
def test_a_wall_of_no_time_is_refused(tmp_path, wall):
    with pytest.raises(ValueError):
        _ran(tmp_path, _Transport(), wall=wall)
