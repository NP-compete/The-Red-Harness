"""An expired token is not a server error, and a pipe is not a person."""

from __future__ import annotations

from typing import Any

import pytest

from agent.cli.approve import decide, is_interactive
from agent.cli.main import UNAUTHENTICATED, main
from agent.cli.transport import Unauthenticated

WAITING: dict[str, Any] = {
    "awaiting": [{"name": "send_email", "args": {"to": "nobody@example.com"}}],
    "resume": {"decisions": ["approve", "deny"]},
}


class TestTheUnauthenticatedExit:
    def test_the_transport_raises_its_own_type(self, monkeypatch):
        from agent.cli import transport as mod

        class _Response:
            status_code = 401
            content = b""
            text = ""

            def json(self) -> dict:
                return {}

        import httpx

        monkeypatch.setattr(httpx, "request", lambda *a, **k: _Response())
        with pytest.raises(Unauthenticated):
            mod.HttpTransport("http://agent.invalid").get("/threads")

    def test_the_entry_point_turns_it_into_4(self, capsys):
        def _boom(*_a: Any, **_k: Any) -> int:
            raise Unauthenticated("nobody knows who you are")

        import agent.cli.main as cli

        original = cli._dispatch
        cli._dispatch = _boom
        try:
            assert main(["thread", "list"]) == UNAUTHENTICATED
        finally:
            cli._dispatch = original

    def test_and_says_so_on_stderr_not_stdout(self, capsys):
        def _boom(*_a: Any, **_k: Any) -> int:
            raise Unauthenticated("nobody knows who you are")

        import agent.cli.main as cli

        original = cli._dispatch
        cli._dispatch = _boom
        try:
            main(["thread", "list"])
        finally:
            cli._dispatch = original
        seen = capsys.readouterr()
        assert "nobody knows who you are" in seen.err
        assert seen.out == ""

    def test_four_is_not_one_of_the_others(self):
        from agent.cli.doctor import DEGRADED_EXIT
        from agent.cli.main import NEEDS_DECISION, USAGE_ERROR

        assert UNAUTHENTICATED not in (0, 1, USAGE_ERROR, NEEDS_DECISION, DEGRADED_EXIT)


class TestWhoIsWatching:
    @pytest.mark.parametrize(
        "stdin,stdout,expected",
        [
            (True, True, True),
            (True, False, False),
            (False, True, False),
            (False, False, False),
        ],
    )
    def test_both_ends_have_to_be_a_terminal(
        self, monkeypatch, stdin, stdout, expected
    ):
        import sys as real_sys

        monkeypatch.setattr(
            real_sys, "stdin", type("x", (), {"isatty": lambda self: stdin})()
        )
        monkeypatch.setattr(
            real_sys, "stdout", type("x", (), {"isatty": lambda self: stdout})()
        )
        assert is_interactive() is expected

    def test_a_piped_run_is_not_asked_to_decide(self, monkeypatch):
        import sys as real_sys

        monkeypatch.setattr(
            real_sys, "stdin", type("x", (), {"isatty": lambda self: True})()
        )
        monkeypatch.setattr(
            real_sys, "stdout", type("x", (), {"isatty": lambda self: False})()
        )
        asked: list[str] = []
        answer = decide(WAITING, ask=lambda prompt: asked.append(prompt) or "approve")
        assert answer is None, "it prompted into a pipeline"
        assert asked == []

    def test_a_person_at_a_terminal_still_gets_the_question(self, monkeypatch):
        import sys as real_sys

        for stream in ("stdin", "stdout"):
            monkeypatch.setattr(
                real_sys, stream, type("x", (), {"isatty": lambda self: True})()
            )
        answer = decide(
            WAITING, ask=lambda _prompt: "approve", write=lambda _line: None
        )
        assert answer is not None and answer.decision == "approve"
