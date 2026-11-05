"""A ceiling nobody sets catches nothing."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

AGENT_YAML = Path(__file__).parents[3] / "config" / "agent" / "runtime" / "agent.yaml"


@pytest.fixture(scope="module")
def limits() -> dict:
    loaded = yaml.safe_load(AGENT_YAML.read_text())
    return loaded["middleware"]["tool_call_limit"]


def test_the_shipped_config_caps_a_block(limits):
    assert limits["per_block"] > 0


def test_a_block_ceiling_leaves_room_for_a_long_answer(limits):
    assert limits["per_block"] >= 10


def test_the_shipped_config_caps_a_conversation(limits):
    assert limits["per_thread"] > 0


def test_the_conversation_ceiling_is_a_runaway_guard_not_a_budget(limits):
    assert limits["per_thread"] >= 1000


def test_the_run_still_continues_when_one_is_spent(limits):
    assert limits.get("on_exceeded", "exclude") == "exclude"
