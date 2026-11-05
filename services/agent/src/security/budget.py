"""Tracks what a run has left to spend."""

from __future__ import annotations

from collections import Counter

from agent.src.agent.config.middleware import ToolCallLimitConfig
from agent.src.security.resolver import Budget, RunContext, ToolCall


class RunBudget:
    """What one run has spent in tool calls and tokens, against its limits."""

    def __init__(
        self, limits: ToolCallLimitConfig, token_limit: int | None = None
    ) -> None:
        """Start an unspent budget under `limits` and `token_limit`."""
        self._limits = limits
        self._token_limit = token_limit
        self._calls: Counter[str] = Counter()
        self._total_calls = 0
        self._tokens = 0

    @property
    def spent(self) -> tuple[int, int]:
        """Tool calls and tokens spent so far."""
        return (self._total_calls, self._tokens)

    def record(self, call: ToolCall) -> None:
        """Charge one tool call against the budget."""
        self._calls[call.name] += 1
        self._total_calls += 1

    def record_tokens(self, tokens: int) -> None:
        """Charge `tokens` against the budget."""
        self._tokens += tokens

    def remaining(self, ctx: RunContext, call: ToolCall | None = None) -> Budget:
        """What is left, overall and for `call` in particular."""
        return Budget(
            tokens_remaining=self._tokens_left(),
            calls_remaining=self._calls_left(call),
        )

    def _tokens_left(self) -> int | None:
        """Tokens left, or `None` when there is no token limit."""
        if self._token_limit is None:
            return None
        return max(0, self._token_limit - self._tokens)

    def _calls_left(self, call: ToolCall | None) -> int | None:
        """Calls left, or `None` when call limits are off."""
        if not self._limits.enabled:
            return None

        left = max(0, self._limits.run_limit - self._total_calls)

        if call is not None:
            ceiling = self._limits.per_tool.get(call.name)
            if ceiling is not None:
                left = min(left, max(0, ceiling - self._calls[call.name]))

        return left
