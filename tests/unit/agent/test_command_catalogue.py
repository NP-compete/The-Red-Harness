"""The commands this agent ships with, and how a typed line becomes a prompt."""

from __future__ import annotations

from agent.src.agent.command_catalogue import SHIPPED, expand, registry


def test_the_agent_ships_with_commands():
    assert SHIPPED


def test_every_shipped_command_explains_itself():
    assert all(command.help.strip() for command in SHIPPED)


def test_every_shipped_command_carries_a_prompt():
    assert all(command.prompt.strip() for command in SHIPPED)


def test_the_palette_is_in_a_settled_order():
    names = [command.name for command in registry().palette()]
    assert names == sorted(names)


def test_an_ordinary_message_is_left_alone():
    assert expand("what is the travel limit?") == "what is the travel limit?"


def test_a_known_command_becomes_its_prompt():
    expanded = expand("/summarise")
    assert expanded != "/summarise"


def test_a_command_argument_is_carried_into_the_prompt():
    assert "the third quarter" in expand("/summarise the third quarter")


def test_an_unknown_command_is_left_for_the_model_to_read():
    assert expand("/nonsense please") == "/nonsense please"


def test_a_bare_slash_is_left_alone():
    assert expand("/") == "/"


def test_a_command_with_no_argument_says_so_rather_than_leaving_a_gap():
    assert "{argument}" not in expand("/summarise")
