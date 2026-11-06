"""Typing a command in a conversation."""

from __future__ import annotations

import pytest

from agent.src.agent.commands import Command, CommandRegistry, Unknown


def registry(*extra: Command) -> CommandRegistry:
    return CommandRegistry(
        shipped=[
            Command(
                name="summarise",
                prompt="Summarise the conversation so far.",
                help="Recap",
            ),
        ],
        declared=list(extra),
    )


def test_plain_text_is_not_a_command():
    assert registry().resolve("what happened last quarter?") is None


def test_a_shipped_command_expands_to_its_prompt():
    assert (
        registry().resolve("/summarise").prompt == "Summarise the conversation so far."
    )


def test_an_unknown_command_is_reported_rather_than_sent_as_text():
    resolved = registry().resolve("/nonsense")
    assert isinstance(resolved, Unknown)
    assert resolved.name == "nonsense"


def test_a_deployment_can_declare_its_own():
    reg = registry(Command(name="handoff", prompt="Hand this over.", help="Hand over"))
    assert reg.resolve("/handoff").prompt == "Hand this over."


def test_a_declared_command_overrides_a_shipped_one_of_the_same_name():
    reg = registry(
        Command(name="summarise", prompt="House summary style.", help="Recap")
    )
    assert reg.resolve("/summarise").prompt == "House summary style."


def test_the_rest_of_the_line_is_passed_through():
    resolved = registry().resolve("/summarise in two sentences")
    assert resolved.argument == "in two sentences"


def test_an_argument_is_empty_when_none_is_given():
    assert registry().resolve("/summarise").argument == ""


def test_the_palette_lists_what_is_available_with_help():
    reg = registry(Command(name="handoff", prompt="Hand this over.", help="Hand over"))
    assert [(c.name, c.help) for c in reg.palette()] == [
        ("handoff", "Hand over"),
        ("summarise", "Recap"),
    ]


def test_the_palette_lists_each_name_once():
    reg = registry(Command(name="summarise", prompt="House style.", help="Recap"))
    assert [c.name for c in reg.palette()] == ["summarise"]


@pytest.mark.parametrize("name", ["approve", "allow", "bypass"])
def test_a_command_cannot_be_named_after_granting_permission(name):
    with pytest.raises(ValueError):
        Command(name=name, prompt="...", help="...")


def test_a_command_carries_no_authority_of_its_own():
    assert not any(
        hasattr(Command(name="x", prompt="p", help="h"), f)
        for f in ("decision", "risk")
    )
