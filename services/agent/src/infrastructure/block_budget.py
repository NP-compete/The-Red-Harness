"""Catching a tool called in a loop, without refusing a long answer."""

from __future__ import annotations

from collections import Counter
from typing import Any

from langchain.agents.middleware import AgentMiddleware

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def _tool_calls(message: Any) -> list[dict]:
    """The tool calls on `message`, if it has any."""
    calls = getattr(message, "tool_calls", None)
    return [c for c in (calls or []) if isinstance(c, dict)]


def spent_in_block(messages: Any, *, per_block: int) -> set[str]:
    """Tools that have used up their allowance in the latest block."""
    if per_block <= 0 or not isinstance(messages, list):
        return set()

    latest: list[dict] = []
    for message in reversed(messages):
        found = _tool_calls(message)
        if found:
            latest = found
            break

    counted = Counter(
        str(call.get("name")) for call in latest if isinstance(call.get("name"), str)
    )
    return {name for name, used in counted.items() if used > per_block}


def spent_in_thread(messages: Any, *, per_thread: int) -> set[str]:
    """Tools that have used up their allowance in the conversation."""
    if per_thread <= 0 or not isinstance(messages, list):
        return set()

    counted: Counter[str] = Counter()
    for message in messages:
        counted.update(
            str(call.get("name"))
            for call in _tool_calls(message)
            if isinstance(call.get("name"), str)
        )
    return {name for name, used in counted.items() if used > per_thread}


def _budget_notice(spent: list[str], limit: int, scope: str) -> Any:
    """What the model is told when a tool is taken away."""
    from langchain_core.messages import SystemMessage

    named = ", ".join(spent)
    return SystemMessage(
        content=(
            f"The call budget for this {scope} is spent for: {named} "
            f"(limit {limit} per {scope}). Those tools are not available "
            "for this step. Answer from what you already have, or take a "
            "different approach — do not wait for them."
        )
    )


class ToolBudgetExceeded(RuntimeError):
    """A spent budget on a deployment that asked to be stopped."""


class BlockBudgetMiddleware(AgentMiddleware):
    """Takes a looping tool away from the next model call."""

    def __init__(self, *, config: Any) -> None:
        """Bind the middleware to `config`."""
        super().__init__()
        self._config = config

    def _spent(self, messages: Any) -> list[tuple[set[str], int, str]]:
        """Each ceiling that something has gone past, with its scope."""
        per_block = int(getattr(self._config, "per_block", 0) or 0)
        per_thread = int(getattr(self._config, "per_thread", 0) or 0)
        found = [
            (spent_in_block(messages, per_block=per_block), per_block, "block"),
            (
                spent_in_thread(messages, per_thread=per_thread),
                per_thread,
                "conversation",
            ),
        ]
        return [over for over in found if over[0]]

    def _allowed(self, request: Any) -> Any:
        """The request with over-budget tools withheld."""
        state = getattr(request, "state", None) or {}
        over = self._spent(state.get("messages"))
        if not over:
            return request

        if getattr(self._config, "on_exceeded", "exclude") == "error":
            spent, limit, scope = over[0]
            raise ToolBudgetExceeded(
                f"{', '.join(sorted(spent))} went past its call budget "
                f"({limit} per {scope})"
            )

        taken = {name for spent, _, _ in over for name in spent}
        for spent, limit, scope in over:
            logger.warning(
                "Tool budget spent in this %s, excluding from the next call: %s "
                "(limit %d per %s)",
                scope,
                ", ".join(sorted(spent)),
                limit,
                scope,
            )
        kept = [t for t in request.tools if getattr(t, "name", "") not in taken]

        messages = list(getattr(request, "messages", None) or [])
        if messages:
            messages += [
                _budget_notice(sorted(spent), limit, scope)
                for spent, limit, scope in over
            ]
            return request.override(tools=kept, messages=messages)
        return request.override(tools=kept)

    def wrap_model_call(self, request: Any, handler: Any) -> Any:
        """Call the model with over-budget tools withheld."""
        return self._recorded(handler(self._allowed(request)), request)

    async def awrap_model_call(self, request: Any, handler: Any) -> Any:
        """Call the model with over-budget tools withheld."""
        return self._recorded(await handler(self._allowed(request)), request)

    def _recorded(self, reply: Any, request: Any) -> Any:
        """Write what was withheld onto the answer, for the reader."""
        over = self._spent((getattr(request, "state", None) or {}).get("messages"))
        if not over:
            return reply

        spent, limit, scope = over[0]
        message = getattr(reply, "result", None)
        if isinstance(message, list):
            message = message[0] if message else None
        extra = getattr(message, "additional_kwargs", None)
        if not isinstance(extra, dict):
            return reply

        notes = extra.setdefault("answer_notes", {})
        if isinstance(notes, dict):
            notes["budget"] = {
                "withheld": sorted(spent),
                "scope": scope,
                "limit": limit,
            }
        return reply
