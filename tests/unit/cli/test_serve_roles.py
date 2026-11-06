"""One command, one role (E10-T19)."""

from __future__ import annotations

import pytest

from agent.cli.serve import RoleFailed, agent_command, command_for, serve


class TestTheRolesThisImageHas:
    def test_agent_is_the_entry_point_the_container_has_always_run(self):
        assert agent_command()[1:] == ["-m", "agent.aegra.entrypoint"]

    def test_ui_refuses_when_nothing_is_built(self, tmp_path):
        with pytest.raises(RoleFailed, match="npm run build"):
            command_for("ui", ui_dir=str(tmp_path))

    def test_ui_runs_the_built_server_not_the_dev_one(self, tmp_path):
        built = tmp_path / "dist" / "server"
        built.mkdir(parents=True)
        (built / "index.js").write_text("")
        assert command_for("ui", ui_dir=str(tmp_path))[-1].endswith(
            "dist/server/index.js"
        )


class TestARoleThisImageCannotServe:
    @pytest.mark.parametrize("role,names", [("acp", "ACP")])
    def test_it_is_refused_by_name(self, role, names):
        with pytest.raises(RoleFailed, match=names):
            command_for(role)

    def test_the_refusal_is_a_non_zero_exit(self):
        # `acp`, not a servable role: `serve` without `exec_` execs for
        # real, and this test used to name `worker` back when the image
        # could not serve it. Once it could, this line replaced the test
        # runner with a Temporal worker — pytest exited 0 at 35% and the
        # remaining 64% of the suite never ran, in silence.
        said = []
        assert serve("acp", write=said.append) == 2
        assert "ACP" in said[0]

    def test_a_role_nobody_has_heard_of_lists_the_ones_there_are(self):
        with pytest.raises(
            RoleFailed, match="agent, ui, worker, eval-worker, opa or all"
        ):
            command_for("nope")


class TestItExecsRatherThanWraps:
    def test_the_process_is_replaced(self):
        called = []
        serve("agent", exec_=lambda path, argv: called.append((path, argv)))
        assert called and called[0][1][1:] == ["-m", "agent.aegra.entrypoint"]

    def test_a_failed_exec_is_reported_rather_than_returning_zero(self):
        assert serve("agent", exec_=lambda *_: None, write=lambda _line: None) == 1


class TestTheSupervisor:
    """`harness all`, for Kind and demos (E10-T19)."""

    def _children(self, monkeypatch, agent_cmd, ui_cmd):
        import agent.cli.serve as module

        monkeypatch.setattr(
            module,
            "command_for",
            lambda role, ui_dir=None: agent_cmd if role == "agent" else ui_cmd,
        )

    def test_a_child_that_fails_decides_the_exit_code(self, monkeypatch):
        import sys

        from agent.cli.serve import supervise

        self._children(
            monkeypatch,
            [sys.executable, "-c", "raise SystemExit(3)"],
            [sys.executable, "-c", "import time; time.sleep(30)"],
        )
        assert supervise(write=lambda _l: None) == 3

    def test_the_first_to_exit_takes_the_other_with_it(self, monkeypatch):
        import sys
        import time

        from agent.cli.serve import supervise

        self._children(
            monkeypatch,
            [sys.executable, "-c", "import time; time.sleep(0.2)"],
            [sys.executable, "-c", "import time; time.sleep(30)"],
        )
        started = time.monotonic()
        assert supervise(write=lambda _l: None) == 0
        assert time.monotonic() - started < 10

    def test_a_role_that_cannot_start_refuses_and_stops_the_other(self, monkeypatch):
        import sys

        import agent.cli.serve as module
        from agent.cli.serve import RoleFailed, supervise

        def refuse(role, ui_dir=None):
            if role == "ui":
                raise RoleFailed("nothing is built")
            return [sys.executable, "-c", "import time; time.sleep(30)"]

        monkeypatch.setattr(module, "command_for", refuse)
        said: list[str] = []
        assert supervise(write=said.append) == 2
        assert "nothing is built" in said[-1]

    def test_it_says_it_is_not_the_production_path(self, monkeypatch):
        import sys

        from agent.cli.serve import supervise

        self._children(
            monkeypatch,
            [sys.executable, "-c", ""],
            [sys.executable, "-c", ""],
        )
        said: list[str] = []
        supervise(write=said.append)
        assert "Production runs one role per container" in said[0]


class TestTheInterfaceRunsFromItsOwnDirectory:
    """The server resolves the built client relative to cwd."""

    def test_it_changes_directory_before_exec(self, tmp_path, monkeypatch):
        from agent.cli.serve import serve

        built = tmp_path / "dist" / "server"
        built.mkdir(parents=True)
        (built / "index.js").write_text("")

        seen: dict = {}
        monkeypatch.setattr("os.chdir", lambda where: seen.update(cwd=str(where)))
        serve(
            "ui",
            ui_dir=str(tmp_path),
            exec_=lambda _p, _a: None,
            write=lambda _l: None,
        )
        assert seen["cwd"] == str(tmp_path)

    def test_the_agent_role_does_not(self, monkeypatch):
        from agent.cli.serve import serve

        moved: list[str] = []
        monkeypatch.setattr("os.chdir", lambda where: moved.append(str(where)))
        serve("agent", exec_=lambda _p, _a: None, write=lambda _l: None)
        assert moved == []
