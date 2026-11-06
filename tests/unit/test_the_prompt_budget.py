"""What a trivial turn sends before anybody types anything (PERF-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROMPT = ROOT / "config" / "agent" / "PROMPT.md"

PER_TOKEN = 4

TARGET_TOKENS = 3000

PROMPT_CEILING_TOKENS = 3400

PLATFORM_CEILING_TOKENS = 1300


def _tokens(text: str) -> int:
    return len(text) // PER_TOKEN


@pytest.fixture(scope="module")
def shipped() -> str:
    """What the loader actually puts in front of the model."""
    from agent.src.agent.config.parser import parse_frontmatter

    return parse_frontmatter(PROMPT)["body"]


@pytest.fixture(scope="module")
def platform_additions(shipped: str) -> int:
    from agent.aegra import graph
    from agent.src.memory.instructions import (
        append_memory_instructions,
        use_compact_memory_prompt,
    )

    use_compact_memory_prompt()
    added = len(append_memory_instructions(shipped)) - len(shipped)
    added += len(graph._SAFETY_STOP_INSTRUCTION)
    added += len(graph._CAPABILITY_RESTRICTION_INSTRUCTION)
    return added // PER_TOKEN


class TestThePlatformsShare:
    def test_it_is_a_few_hundred_tokens(self, platform_additions):
        assert platform_additions <= PLATFORM_CEILING_TOKENS, (
            f"the platform now adds {platform_additions} tokens to every "
            f"system prompt, over its own budget of {PLATFORM_CEILING_TOKENS}. "
            "This part is not the operator's prompt — it is what this "
            "template puts in front of it."
        )

    def test_the_compact_memory_preamble_is_the_one_in_use(self, shipped):
        """It is 532 characters instead of 5,120."""
        from agent.src.memory.instructions import (
            append_memory_instructions,
            use_compact_memory_prompt,
        )

        use_compact_memory_prompt()
        compact = len(append_memory_instructions(shipped))
        assert compact - len(shipped) < 5000


class TestTheShippedPromptOnlyShrinks:
    def test_it_is_under_the_ratchet(self, shipped):
        count = _tokens(shipped)
        assert count <= PROMPT_CEILING_TOKENS, (
            f"PROMPT.md is {count} tokens, over the ceiling of "
            f"{PROMPT_CEILING_TOKENS}. Every turn pays this before the "
            "person has typed anything. Lower the ceiling when you cut it; "
            "do not raise it."
        )

    def test_the_ratchet_is_honest_about_the_gap(self):
        assert PROMPT_CEILING_TOKENS > TARGET_TOKENS, (
            "the ceiling has reached the target — PERF-3 is met, so delete "
            "this test and assert the target directly"
        )

    def test_the_ceiling_is_close_to_the_real_size(self, shipped):
        """A ceiling far above the truth is not a ratchet."""
        assert _tokens(shipped) > PROMPT_CEILING_TOKENS * 0.9


class TestTheWholeSystemPrompt:
    def test_it_misses_perf_3_and_that_is_recorded(self, shipped, platform_additions):
        """Written as an inequality so it cannot pass hollow."""
        whole = _tokens(shipped) + platform_additions
        assert whole > TARGET_TOKENS, (
            f"the system prompt is now {whole} tokens, inside PERF-3's "
            f"{TARGET_TOKENS}. Flip PERF-3 in the PRD and replace this file "
            "with a plain assertion against the target."
        )


class TestThePlatformsShareIsGated:
    """The 1,036-token memory block is not sent unconditionally."""

    def test_the_memory_block_is_behind_the_flag(self):
        import inspect

        from agent.aegra import graph

        source = inspect.getsource(graph.agent)
        gated = source.index("if user_memory_enabled:")
        appended = source.index("_append_memory_instructions(system_prompt)")
        assert gated < appended, (
            "the memory instructions are appended outside the "
            "`user_memory_enabled` check, so a deployment with memory off "
            "pays 1,036 tokens a turn for instructions about a tool it does "
            "not have"
        )

    def test_a_user_preference_can_turn_it_off(self):
        import inspect

        from agent.aegra import graph

        source = inspect.getsource(graph.agent)
        assert "user_prefs.memory_enabled" in source
