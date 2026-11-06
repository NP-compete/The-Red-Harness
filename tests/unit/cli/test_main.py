"""The command line itself: what it prints and what it returns."""

from __future__ import annotations

import json

import pytest

from agent.cli.doctor import DEGRADED_EXIT
from agent.cli.main import USAGE_ERROR, main


def run(argv: list[str], capsys, **probes) -> tuple[int, str]:
    code = main(argv, probes=lambda: dict(probes))
    return code, capsys.readouterr().out


HEALTHY = {
    "agent_reachable": True,
    "config_readable": True,
    "override_store": True,
    "model_key_present": True,
    "tracing_configured": True,
}


class TestDoctor:
    def test_a_healthy_deployment_succeeds(self, capsys):
        code, _ = run(["doctor"], capsys, **HEALTHY)
        assert code == 0

    def test_and_says_so_rather_than_printing_nothing(self, capsys):
        _, out = run(["doctor"], capsys, **HEALTHY)
        assert out.strip()

    def test_a_blocked_deployment_fails(self, capsys):
        code, _ = run(["doctor"], capsys, **{**HEALTHY, "agent_reachable": False})
        assert code == 1

    def test_it_names_what_is_wrong(self, capsys):
        _, out = run(["doctor"], capsys, **{**HEALTHY, "agent_reachable": False})
        assert "agent" in out.lower()

    def test_it_says_what_to_do_about_it(self, capsys):
        _, out = run(["doctor"], capsys, **{**HEALTHY, "model_key_present": False})
        assert "credential" in out.lower()


class TestJson:
    def test_it_prints_json_when_asked(self, capsys):
        _, out = run(["doctor", "--json"], capsys, **HEALTHY)
        assert json.loads(out)["ok"] is True

    def test_the_exit_code_is_the_same_either_way(self, capsys):
        plain, _ = run(["doctor"], capsys, **{**HEALTHY, "override_store": False})
        encoded, _ = run(
            ["doctor", "--json"], capsys, **{**HEALTHY, "override_store": False}
        )
        assert plain == encoded == DEGRADED_EXIT

    def test_it_prints_nothing_but_json(self, capsys):
        _, out = run(
            ["doctor", "--json"], capsys, **{**HEALTHY, "agent_reachable": False}
        )
        json.loads(out)


class TestWhatItWillNotDo:
    def test_it_refuses_a_command_it_does_not_have(self, capsys):
        with pytest.raises(SystemExit):
            main(["deploy"], probes=lambda: dict(HEALTHY))

    def test_it_says_what_it_can_do_when_given_nothing(self, capsys):
        code, out = run([], capsys, **HEALTHY)
        assert code == USAGE_ERROR
        assert "doctor" in out


class TestAsk:
    """Exit codes a pipeline can branch on."""

    @staticmethod
    def _ask(argv, answer=None, fails=None, capsys=None):
        from agent.cli.ask import Answer, AskFailed
        from agent.cli.main import main

        def asker(question, **_kwargs):
            if fails:
                raise AskFailed(fails)
            return answer or Answer(text="The limit is 750.", thread_id="t1")

        code = main(argv, probes=lambda: dict(HEALTHY), asker=asker)
        seen = capsys.readouterr()
        return code, seen.out + seen.err

    def test_an_answered_question_succeeds(self, capsys):
        code, _ = self._ask(["ask", "what is the limit?"], capsys=capsys)
        assert code == 0

    def test_it_prints_the_answer_and_nothing_else(self, capsys):
        _, out = self._ask(["ask", "what is the limit?"], capsys=capsys)
        assert out.strip() == "The limit is 750."

    def test_json_carries_the_conversation_too(self, capsys):
        _, out = self._ask(["ask", "q", "--json"], capsys=capsys)
        assert json.loads(out)["thread_id"] == "t1"

    def test_json_carries_the_answer(self, capsys):
        _, out = self._ask(["ask", "q", "--json"], capsys=capsys)
        assert json.loads(out)["answer"] == "The limit is 750."

    def test_a_failure_is_not_success(self, capsys):
        code, _ = self._ask(["ask", "q"], fails="the agent said no", capsys=capsys)
        assert code == 1

    def test_a_failure_says_why(self, capsys):
        _, out = self._ask(["ask", "q"], fails="the agent said no", capsys=capsys)
        assert "the agent said no" in out

    def test_a_failure_in_json_is_still_json(self, capsys):
        _, out = self._ask(["ask", "q", "--json"], fails="nope", capsys=capsys)
        assert json.loads(out)["ok"] is False

    def test_a_failure_in_json_carries_the_reason(self, capsys):
        _, out = self._ask(["ask", "q", "--json"], fails="nope", capsys=capsys)
        assert json.loads(out)["error"] == "nope"


class TestThreadCommands:
    @staticmethod
    def _run(argv, capsys, rows=None, fails=None):
        from agent.cli.main import main
        from agent.cli.threads import ThreadFailed, ThreadRow

        class _Ops:
            def list_threads(self, **_):
                if fails:
                    raise ThreadFailed(fails)
                return (
                    rows
                    if rows is not None
                    else [
                        ThreadRow(thread_id="t1", title="Travel limits", status="idle"),
                    ]
                )

            def show_thread(self, thread_id, **_):
                if fails:
                    raise ThreadFailed(fails)
                return {"values": {"messages": []}}

            def remove_thread(self, thread_id, **_):
                if fails:
                    raise ThreadFailed(fails)

            def fork_thread(self, thread_id, **_):
                if fails:
                    raise ThreadFailed(fails)
                return "t2"

        code = main(argv, probes=lambda: dict(HEALTHY), threads=_Ops())
        return code, capsys.readouterr().out

    def test_listing_succeeds(self, capsys):
        code, _ = self._run(["thread", "list"], capsys)
        assert code == 0

    def test_listing_names_each_conversation(self, capsys):
        _, out = self._run(["thread", "list"], capsys)
        assert "t1" in out and "Travel limits" in out

    def test_listing_nothing_says_so_rather_than_printing_blank(self, capsys):
        _, out = self._run(["thread", "list"], capsys, rows=[])
        assert out.strip()

    def test_listing_as_json_is_a_list(self, capsys):
        _, out = self._run(["thread", "list", "--json"], capsys)
        assert isinstance(json.loads(out)["threads"], list)

    def test_a_refusal_is_not_success(self, capsys):
        code, _ = self._run(["thread", "list"], capsys, fails="not allowed")
        assert code == 1

    def test_showing_prints_the_state_as_json(self, capsys):
        _, out = self._run(["thread", "show", "t1"], capsys)
        assert "messages" in json.loads(out)["values"]

    def test_removing_succeeds_quietly(self, capsys):
        code, _ = self._run(["thread", "rm", "t1"], capsys)
        assert code == 0

    def test_forking_reports_the_new_conversation(self, capsys):
        _, out = self._run(["thread", "fork", "t1"], capsys)
        assert "t2" in out


class TestErrorsGoWhereErrorsGo:
    """`id=$(harness thread fork x)` must not capture a complaint."""

    @staticmethod
    def _run(argv, capsys, fails="refused"):
        from agent.cli.ask import AskFailed
        from agent.cli.main import main
        from agent.cli.threads import ThreadFailed

        def asker(_q, **_k):
            raise AskFailed(fails)

        class _Ops:
            def fork_thread(self, *_a, **_k):
                raise ThreadFailed(fails)

            def list_threads(self, **_k):
                raise ThreadFailed(fails)

        code = main(argv, probes=lambda: dict(HEALTHY), asker=asker, threads=_Ops())
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    def test_a_failed_question_says_nothing_on_stdout(self, capsys):
        _, out, _ = self._run(["ask", "q"], capsys)
        assert out.strip() == ""

    def test_and_says_it_on_stderr(self, capsys):
        _, _, err = self._run(["ask", "q"], capsys)
        assert "refused" in err

    def test_a_failed_fork_says_nothing_on_stdout(self, capsys):
        _, out, _ = self._run(["thread", "fork", "t1"], capsys)
        assert out.strip() == ""

    def test_a_failed_listing_says_nothing_on_stdout(self, capsys):
        _, out, _ = self._run(["thread", "list"], capsys)
        assert out.strip() == ""

    def test_json_errors_also_go_to_stderr(self, capsys):
        _, out, err = self._run(["ask", "q", "--json"], capsys)
        assert out.strip() == ""
        assert json.loads(err)["ok"] is False


class TestRunCommands:
    @staticmethod
    def _run(argv, capsys, rows=None, fails=None):
        from agent.cli.main import main
        from agent.cli.runs import RunFailed, RunRow

        class _Ops:
            def list_runs(self, thread_id, **_):
                if fails:
                    raise RunFailed(fails)
                return (
                    rows
                    if rows is not None
                    else [
                        RunRow(
                            run_id="r1",
                            status="running",
                            error="",
                            created_at="2026-10-28T10:00:00Z",
                        ),
                        RunRow(
                            run_id="r2",
                            status="error",
                            error="the model refused",
                            created_at="2026-10-28T10:05:00Z",
                        ),
                    ]
                )

            def show_run(self, thread_id, run_id, **_):
                if fails:
                    raise RunFailed(fails)
                return {"run_id": run_id, "status": "running"}

            def cancel_run(self, thread_id, run_id, **_):
                if fails:
                    raise RunFailed(fails)

            def unfinished(self, rows):
                from agent.cli.runs import unfinished

                return unfinished(rows)

        code = main(argv, probes=lambda: dict(HEALTHY), runs=_Ops())
        seen = capsys.readouterr()
        return code, seen.out, seen.err

    def test_listing_succeeds(self, capsys):
        code, _, _ = self._run(["run", "list", "t1"], capsys)
        assert code == 0

    def test_listing_shows_why_one_failed(self, capsys):
        _, out, _ = self._run(["run", "list", "t1"], capsys)
        assert "the model refused" in out

    def test_listing_as_json_carries_the_reason_too(self, capsys):
        _, out, _ = self._run(["run", "list", "t1", "--json"], capsys)
        assert json.loads(out)["runs"][1]["error"] == "the model refused"

    def test_nothing_to_show_says_so(self, capsys):
        _, out, _ = self._run(["run", "list", "t1"], capsys, rows=[])
        assert out.strip()

    def test_showing_prints_the_run(self, capsys):
        _, out, _ = self._run(["run", "show", "t1", "r1"], capsys)
        assert json.loads(out)["run_id"] == "r1"

    def test_cancelling_succeeds(self, capsys):
        code, _, _ = self._run(["run", "cancel", "t1", "r1"], capsys)
        assert code == 0

    def test_a_refusal_is_not_success(self, capsys):
        code, _, _ = self._run(
            ["run", "cancel", "t1", "r1"], capsys, fails="already finished"
        )
        assert code == 1

    def test_a_refusal_goes_to_the_error_stream(self, capsys):
        _, out, err = self._run(
            ["run", "cancel", "t1", "r1"], capsys, fails="already finished"
        )
        assert out.strip() == "" and "already finished" in err


class TestInventoryCommands:
    @staticmethod
    def _run(argv, capsys, fails=None):
        from agent.cli.inventory import InventoryFailed, Server, Skill
        from agent.cli.main import main

        class _Ops:
            def list_servers(self, **_):
                if fails:
                    raise InventoryFailed(fails)
                return [
                    Server(
                        name="atlan",
                        display_name="Atlan",
                        enabled=True,
                        auth_mode="dcr",
                        connected=True,
                        account="a@b.c",
                    ),
                    Server(
                        name="gitlab",
                        display_name="GitLab",
                        enabled=True,
                        auth_mode="none",
                        connected=False,
                        account="",
                    ),
                    Server(
                        name="miro",
                        display_name="Miro",
                        enabled=True,
                        auth_mode="dcr",
                        connected=None,
                        account="",
                    ),
                ]

            def list_skills(self, **_):
                if fails:
                    raise InventoryFailed(fails)
                return [Skill(name="data-discovery", description="Find a dataset.")]

        code = main(argv, probes=lambda: dict(HEALTHY), inventory=_Ops())
        seen = capsys.readouterr()
        return code, seen.out, seen.err

    def test_listing_servers_succeeds(self, capsys):
        code, _, _ = self._run(["mcp", "list"], capsys)
        assert code == 0

    def test_it_says_which_are_usable(self, capsys):
        _, out, _ = self._run(["mcp", "list"], capsys)
        assert "atlan" in out and "gitlab" in out

    def test_a_connection_nobody_could_check_is_not_called_disconnected(self, capsys):
        _, out, _ = self._run(["mcp", "list"], capsys)
        assert "unknown" in out.lower()

    def test_json_carries_the_connection_state(self, capsys):
        _, out, _ = self._run(["mcp", "list", "--json"], capsys)
        found = {s["name"]: s for s in json.loads(out)["servers"]}
        assert found["atlan"]["connected"] is True
        assert found["miro"]["connected"] is None

    def test_listing_skills_succeeds(self, capsys):
        code, out, _ = self._run(["skill", "list"], capsys)
        assert code == 0 and "data-discovery" in out

    def test_a_refusal_is_not_success(self, capsys):
        code, out, err = self._run(["mcp", "list"], capsys, fails="not allowed")
        assert code == 1 and out.strip() == "" and "not allowed" in err


class TestTheExitCodesAreDocumented:
    """A code nobody wrote down is a code nobody can rely on."""

    def test_the_help_says_what_they_mean(self, capsys):
        from agent.cli.main import main

        with pytest.raises(SystemExit):
            main(["--help"], probes=lambda: dict(HEALTHY))
        out = capsys.readouterr().out
        assert "exit" in out.lower()

    def test_it_names_the_usable_case(self, capsys):
        from agent.cli.main import main

        with pytest.raises(SystemExit):
            main(["--help"], probes=lambda: dict(HEALTHY))
        assert "0" in capsys.readouterr().out


class TestObserve:
    @staticmethod
    def _run(argv, capsys, findings=None, fails=None):
        from agent.cli.main import main
        from agent.cli.observe import Findings, ObserveFailed
        from agent.src.improvement.mine import Observation

        class _Ops:
            def collect(self, **_):
                if fails:
                    raise ObserveFailed(fails)
                return findings or Findings(
                    observations=[
                        Observation(
                            kind="tool_abandoned",
                            detail="sql was called and its result unused",
                            run_id="t1",
                            runs=["t1", "t2"],
                            seen=2,
                            last_seen="2026-10-28T10:00:00Z",
                        )
                    ],
                    read=9,
                    unreadable=1,
                )

        code = main(argv, probes=lambda: dict(HEALTHY), observer=_Ops())
        seen = capsys.readouterr()
        return code, seen.out, seen.err

    def test_it_succeeds(self, capsys):
        code, _, _ = self._run(["observe"], capsys)
        assert code == 0

    def test_it_names_what_it_saw(self, capsys):
        _, out, _ = self._run(["observe"], capsys)
        assert "tool_abandoned" in out

    def test_it_says_how_often(self, capsys):
        _, out, _ = self._run(["observe"], capsys)
        assert "2" in out

    def test_it_says_how_much_it_read(self, capsys):
        _, out, _ = self._run(["observe"], capsys)
        assert "9" in out

    def test_it_admits_what_it_could_not_read(self, capsys):
        _, out, _ = self._run(["observe"], capsys)
        assert "1" in out and "could not" in out.lower()

    def test_nothing_found_still_says_what_was_looked_at(self, capsys):
        from agent.cli.observe import Findings

        _, out, _ = self._run(["observe"], capsys, findings=Findings(read=40))
        assert "40" in out

    def test_json_carries_the_observations(self, capsys):
        _, out, _ = self._run(["observe", "--json"], capsys)
        assert json.loads(out)["observations"][0]["kind"] == "tool_abandoned"

    def test_json_carries_the_coverage(self, capsys):
        _, out, _ = self._run(["observe", "--json"], capsys)
        body = json.loads(out)
        assert body["read"] == 9 and body["unreadable"] == 1

    def test_a_failure_is_not_success(self, capsys):
        code, out, err = self._run(["observe"], capsys, fails="not allowed")
        assert code == 1 and out.strip() == "" and "not allowed" in err


class TestAskWhenTheRunIsWaiting:
    """A queue, not an incident — and a pipeline must be able to tell."""

    @staticmethod
    def _ask(argv, capsys):
        from agent.cli.ask import Answer
        from agent.cli.main import main

        def asker(_q, **_k):
            return Answer(
                text="",
                thread_id="t1",
                paused={
                    "status": "needs_approval",
                    "awaiting": [
                        {"action": "execute_sql", "args": {}, "description": "Run?"}
                    ],
                    "resume": {"thread_id": "t1", "decisions": ["approve", "reject"]},
                },
            )

        code = main(argv, probes=lambda: dict(HEALTHY), asker=asker)
        seen = capsys.readouterr()
        return code, seen.out, seen.err

    def test_it_is_not_reported_as_success(self, capsys):
        code, _, _ = self._ask(["ask", "q"], capsys)
        assert code != 0

    def test_nor_as_a_failure(self, capsys):
        code, _, _ = self._ask(["ask", "q"], capsys)
        assert code != 1

    def test_it_has_its_own_code(self, capsys):
        code, _, _ = self._ask(["ask", "q"], capsys)
        assert code == 3

    def test_it_says_what_is_waiting(self, capsys):
        _, _, err = self._ask(["ask", "q"], capsys)
        assert "execute_sql" in err

    def test_it_says_how_to_continue(self, capsys):
        _, _, err = self._ask(["ask", "q"], capsys)
        assert "t1" in err

    def test_nothing_that_looks_like_an_answer_goes_to_stdout(self, capsys):
        _, out, _ = self._ask(["ask", "q"], capsys)
        assert out.strip() == ""

    def test_json_carries_the_whole_pause(self, capsys):
        _, out, err = self._ask(["ask", "q", "--json"], capsys)
        body = json.loads(err or out)
        assert body["status"] == "needs_approval"
        assert body["resume"]["thread_id"] == "t1"

    def test_the_help_documents_the_code(self, capsys):
        from agent.cli.main import main

        with pytest.raises(SystemExit):
            main(["--help"], probes=lambda: dict(HEALTHY))
        assert "3" in capsys.readouterr().out


class TestNothingButDataOnStdout:
    """Libraries log. A command line's stdout is its return value."""

    def test_the_http_client_is_quietened(self):
        import logging

        from agent.cli.main import quieten_libraries

        logging.getLogger("httpx").setLevel(logging.INFO)
        quieten_libraries()
        assert logging.getLogger("httpx").level >= logging.WARNING

    def test_so_is_its_transport(self):
        import logging

        from agent.cli.main import quieten_libraries

        quieten_libraries()
        assert logging.getLogger("httpcore").level >= logging.WARNING

    def test_nothing_a_library_logs_reaches_stdout(self, capsys):
        import logging

        from agent.cli.main import quieten_libraries

        quieten_libraries()
        logging.getLogger("httpx").info("HTTP Request: POST /threads")
        assert capsys.readouterr().out == ""

    def test_a_warning_still_gets_through(self, capsys):
        import logging

        from agent.cli.main import quieten_libraries

        quieten_libraries()
        assert logging.getLogger("httpx").isEnabledFor(logging.WARNING)

    def test_the_entry_point_quietens_before_doing_anything(self):
        import inspect

        from agent.cli import main as cli

        source = inspect.getsource(cli.main)
        assert "quieten_libraries()" in source
