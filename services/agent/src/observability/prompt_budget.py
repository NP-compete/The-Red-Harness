"""What a turn spends before the person has said anything."""

from __future__ import annotations

from dataclasses import dataclass

_CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class TurnBudget:
    """Where one turn's tokens went."""

    input_tokens: int
    output_tokens: int
    question_tokens: int
    cached_tokens: int = 0

    @property
    def prompt_tokens(self) -> int:
        """The whole prompt, whether billed or read from cache."""
        return self.input_tokens + self.cached_tokens

    @property
    def overhead_tokens(self) -> int:
        """Everything sent that the person did not type."""
        return max(0, self.prompt_tokens - self.question_tokens)

    @property
    def overhead_share(self) -> float:
        """What share of the prompt was overhead rather than the question."""
        return share_of_prompt(self.overhead_tokens, self.prompt_tokens)


def summarise_turn(
    *,
    input_tokens: int,
    output_tokens: int,
    question: str,
    cached_tokens: int = 0,
) -> TurnBudget:
    """What one turn sent, split into the question and everything else."""
    return TurnBudget(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        question_tokens=len(question) // _CHARS_PER_TOKEN,
        cached_tokens=cached_tokens,
    )


def share_of_prompt(section_tokens: int, total_tokens: int) -> float:
    """How much of the prompt one part accounts for, from 0 to 1."""
    if total_tokens <= 0:
        return 0.0
    return min(1.0, section_tokens / total_tokens)


_SECTIONS = (
    ("instructions", "You are"),
    ("skills", "# Skills"),
    ("memory", "<agent_memory>"),
    ("tool_schemas", '{"name"'),
)


def split_prompt(prompt: str) -> dict[str, int]:
    """How many characters each part of the prompt accounts for."""
    if not prompt:
        return {}

    found = []
    for name, marker in _SECTIONS:
        at = prompt.find(marker)
        if at >= 0:
            found.append((at, name))
    if not found:
        return {}

    found.sort()
    sizes: dict[str, int] = {}
    for index, (at, name) in enumerate(found):
        end = found[index + 1][0] if index + 1 < len(found) else len(prompt)
        sizes[name] = end - at

    if found[0][0] > 0:
        sizes[found[0][1]] += found[0][0]
    return sizes
