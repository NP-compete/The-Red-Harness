"""The reference and the completions are generated (E28-T12)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.cli.main import build_parser
from agent.cli.reference import SHELLS, completion, reference

DOCS = Path(__file__).resolve().parents[3] / "docs" / "reference" / "cli.md"


@pytest.fixture
def parser():
    return build_parser()


class TestThePage:
    def test_every_command_is_on_it(self, parser):
        page = reference(parser)
        for command in ("ask", "config", "observe", "propose", "agent", "doctor"):
            assert f"## `harness {command}`" in page

    def test_so_are_the_flags_that_change_what_happens(self, parser):
        assert "`--follow`" in reference(parser)

    def test_the_exit_codes_are_on_it(self, parser):
        assert "exit codes" in reference(parser)

    def test_help_is_not_a_row_on_every_command(self, parser):
        assert "show this help message" not in reference(parser)

    def test_a_subcommand_gets_its_own_heading(self, parser):
        assert "### `harness config set`" in reference(parser)


class TestTheCompletions:
    @pytest.mark.parametrize("shell", SHELLS)
    def test_each_shell_gets_the_commands(self, shell, parser):
        assert "observe" in completion(shell, parser)

    @pytest.mark.parametrize("shell", SHELLS)
    def test_each_says_how_to_install_it(self, shell, parser):
        assert "harness completion" in completion(shell, parser)

    def test_a_shell_nobody_supports_says_which_are(self, parser):
        with pytest.raises(ValueError, match="bash, zsh, fish"):
            completion("csh", parser)

    @pytest.mark.parametrize("shell", SHELLS)
    def test_nothing_is_run_to_complete(self, shell, parser):
        runnable = [
            line
            for line in completion(shell, parser).splitlines()
            if not line.lstrip().startswith("#")
        ]
        assert not [
            line for line in runnable if "$(harness" in line or "`harness" in line
        ]


class TestThePageIsNotStale:
    def test_the_committed_file_matches_the_parser(self, parser):
        assert DOCS.read_text() == reference(parser)
