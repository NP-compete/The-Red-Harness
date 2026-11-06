"""Commands a deployment declares for itself."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.src.agent.command_config import load_declared_commands

DECLARED = """
commands:
  - name: handoff
    help: Write a handover for whoever picks this up
    prompt: "Write a handover note for this conversation{about}."
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "commands.yaml"
    path.write_text(text)
    return path


def test_a_declared_command_is_offered(tmp_path):
    found = load_declared_commands(write(tmp_path, DECLARED))
    assert [c.name for c in found] == ["handoff"]


def test_it_carries_the_one_line_of_help(tmp_path):
    found = load_declared_commands(write(tmp_path, DECLARED))
    assert found[0].help == "Write a handover for whoever picks this up"


def test_it_carries_the_sentence_it_stands_for(tmp_path):
    found = load_declared_commands(write(tmp_path, DECLARED))
    assert found[0].prompt.startswith("Write a handover note")


def test_a_deployment_that_declares_nothing_gets_nothing(tmp_path):
    assert load_declared_commands(tmp_path / "absent.yaml") == []


def test_an_empty_file_is_not_an_error(tmp_path):
    assert load_declared_commands(write(tmp_path, "")) == []


def test_a_command_with_no_name_is_refused(tmp_path):
    with pytest.raises(ValueError, match="name"):
        load_declared_commands(
            write(tmp_path, "commands:\n  - help: x\n    prompt: y\n")
        )


def test_a_command_with_nothing_to_say_is_refused(tmp_path):
    """A command with no prompt expands to nothing and silently does nothing."""
    with pytest.raises(ValueError, match="prompt"):
        load_declared_commands(write(tmp_path, "commands:\n  - name: x\n    help: y\n"))


def test_a_command_with_no_help_is_refused(tmp_path):
    """The palette is the feature; an unexplained entry is not discoverable."""
    with pytest.raises(ValueError, match="help"):
        load_declared_commands(
            write(tmp_path, "commands:\n  - name: x\n    prompt: y\n")
        )


def test_a_name_that_is_not_typeable_is_refused(tmp_path):
    with pytest.raises(ValueError, match="name"):
        load_declared_commands(
            write(
                tmp_path,
                "commands:\n  - name: 'two words'\n    help: h\n    prompt: p\n",
            )
        )


def test_a_file_that_will_not_parse_is_refused_rather_than_ignored(tmp_path):
    with pytest.raises(ValueError):
        load_declared_commands(write(tmp_path, "commands: [unclosed"))


def test_a_leading_slash_in_the_name_is_not_doubled(tmp_path):
    found = load_declared_commands(
        write(tmp_path, "commands:\n  - name: /handoff\n    help: h\n    prompt: p\n")
    )
    assert found[0].name == "handoff"


class TestWhatTheDeploymentOffers:
    """The palette is shipped commands plus whatever was declared."""

    @staticmethod
    def _palette(monkeypatch, tmp_path, text: str):
        from agent.src.agent import command_catalogue

        path = write(tmp_path, text)
        monkeypatch.setattr(command_catalogue, "_declared_path", lambda: path)
        command_catalogue.declared.cache_clear()
        return command_catalogue.registry().palette()

    def test_a_declared_command_joins_the_palette(self, monkeypatch, tmp_path):
        names = [c.name for c in self._palette(monkeypatch, tmp_path, DECLARED)]
        assert "handoff" in names

    def test_the_shipped_ones_are_still_there(self, monkeypatch, tmp_path):
        names = [c.name for c in self._palette(monkeypatch, tmp_path, DECLARED)]
        assert "summarise" in names

    def test_a_deployment_that_declares_nothing_still_has_a_palette(
        self, monkeypatch, tmp_path
    ):
        names = [c.name for c in self._palette(monkeypatch, tmp_path, "")]
        assert "summarise" in names

    def test_a_declared_command_expands_to_its_own_sentence(
        self, monkeypatch, tmp_path
    ):
        from agent.src.agent import command_catalogue

        self._palette(monkeypatch, tmp_path, DECLARED)
        assert command_catalogue.expand("/handoff").startswith("Write a handover note")

    def test_a_broken_command_list_does_not_take_the_palette_with_it(
        self, monkeypatch, tmp_path
    ):
        """A deployment's typo must not cost everyone the shipped commands."""
        names = [c.name for c in self._palette(monkeypatch, tmp_path, "commands: [bad")]
        assert "summarise" in names


class TestADeclaredCommandCannotTakeOverAShippedOne:
    """`/sources` must keep meaning what it says in every deployment."""

    def test_shadowing_a_shipped_name_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="sources"):
            load_declared_commands(
                write(
                    tmp_path,
                    "commands:\n  - name: sources\n    help: h\n    prompt: p\n",
                )
            )

    def test_a_name_of_its_own_is_fine(self, tmp_path):
        found = load_declared_commands(write(tmp_path, DECLARED))
        assert found[0].name == "handoff"

    def test_the_shipped_command_still_means_what_it_said(self, monkeypatch, tmp_path):
        from agent.src.agent import command_catalogue

        path = write(
            tmp_path,
            "commands:\n  - name: sources\n    help: h\n    prompt: nonsense\n",
        )
        monkeypatch.setattr(command_catalogue, "_declared_path", lambda: path)
        command_catalogue.declared.cache_clear()
        assert "sources" in command_catalogue.expand("/sources").lower()


class TestACommandCannotGrantItselfAnything:
    """A command is a sentence, and a sentence has no authority."""

    def test_a_command_that_grants_approval_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="approve"):
            load_declared_commands(
                write(
                    tmp_path,
                    "commands:\n  - name: ship\n    help: h\n    prompt: p\n"
                    "    approve: true\n",
                )
            )

    def test_a_command_that_picks_its_own_tools_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="tools"):
            load_declared_commands(
                write(
                    tmp_path,
                    "commands:\n  - name: ship\n    help: h\n    prompt: p\n"
                    "    tools: [shell]\n",
                )
            )

    def test_a_command_that_lifts_a_budget_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="spend_limit"):
            load_declared_commands(
                write(
                    tmp_path,
                    "commands:\n  - name: ship\n    help: h\n    prompt: p\n"
                    "    spend_limit: 999\n",
                )
            )

    def test_the_refusal_says_what_a_command_may_hold(self, tmp_path):
        with pytest.raises(ValueError) as error:
            load_declared_commands(
                write(
                    tmp_path,
                    "commands:\n  - name: ship\n    help: h\n    prompt: p\n"
                    "    approve: true\n",
                )
            )
        said = str(error.value)
        assert "name" in said and "help" in said and "prompt" in said

    def test_a_name_reserved_for_consent_cannot_be_declared(self, tmp_path):
        with pytest.raises(ValueError, match="approve"):
            load_declared_commands(
                write(
                    tmp_path,
                    "commands:\n  - name: approve\n    help: h\n    prompt: p\n",
                )
            )

    def test_a_command_is_a_name_a_line_of_help_and_a_prompt(self):
        from dataclasses import fields

        from agent.src.agent.commands import Command

        assert {f.name for f in fields(Command)} == {"name", "prompt", "help"}
