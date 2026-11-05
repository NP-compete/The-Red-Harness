"""Keeping a run inside its allowance, while it runs."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelResponse

from agent.src.security.spend_cap import SpendCap
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def _spent_on(response: Any) -> Decimal | None:
    """What one model call cost, or None when it cannot be known."""
    messages = getattr(response, "result", None) or []
    usage = next(
        (
            getattr(m, "usage_metadata", None)
            for m in messages
            if getattr(m, "usage_metadata", None)
        ),
        None,
    )
    if not usage:
        return None

    from agent.aegra.rates_routes import cost_of_thread

    priced = cost_of_thread(
        {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
        }
    )
    if priced.get("cost") is None:
        return None
    try:
        return Decimal(str(priced["cost"]))
    except InvalidOperation:
        return None


class SpendLimitMiddleware(AgentMiddleware):
    """Stops a run that reaches its spending ceiling."""

    def __init__(
        self,
        *,
        warn_at: Decimal | None = None,
        refuse_at: Decimal | None = None,
        currency: str = "",
        on_spent: Callable[..., Awaitable[None]] | None = None,
    ) -> None:
        """Warn at `warn_at` and refuse at `refuse_at`, having spent nothing."""
        super().__init__()
        self._cap = SpendCap(warn_at=warn_at, refuse_at=refuse_at, currency=currency)
        self.spent = Decimal("0")
        self.unpriced_calls = 0
        self._to_say: str | None = None
        self._on_spent = on_spent

    async def aafter_agent(self, state: Any, runtime: Any = None) -> None:
        """Report what this run cost, against whoever asked for it."""
        if self._on_spent is None:
            return None
        if self.spent <= 0 and not self.unpriced_calls:
            return None

        from agent.src.infrastructure.backend import (
            _get_user_id_from_runtime,
            attribution_from_runtime,
        )

        caller = _get_user_id_from_runtime(runtime) if runtime is not None else None
        if not caller:
            return None

        try:
            await self._on_spent(
                caller, self.spent, context=attribution_from_runtime(runtime)
            )
        except Exception as error:
            logger.warning("Could not record what the run spent: %s", error)
        return None

    def before_agent(self, state: Any, runtime: Any = None) -> None:
        """Start each run from nothing."""
        self.spent = Decimal("0")
        self.unpriced_calls = 0
        self._to_say = None
        self._cap = SpendCap(
            warn_at=self._cap.warn_at,
            refuse_at=self._cap.refuse_at,
            currency=self._cap.currency,
        )
        return None

    async def abefore_agent(self, state: Any, runtime: Any = None) -> None:
        """Run the before-agent hook."""
        return self.before_agent(state, runtime)

    async def awrap_model_call(
        self,
        request: Any,
        handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Refuse if the cap is reached, otherwise call and account for the cost."""
        refusal = self._refusal()
        if refusal is not None:
            return refusal

        response = await handler(request)
        self._account_for(response)
        self._note_warning(response)
        return response

    def _refusal(self) -> Any | None:
        """The answer to give instead of making another call."""
        verdict = self._cap.check(self.spent)
        if verdict is None:
            return None

        if not verdict.refuse:
            self._to_say = verdict.message
            return None

        logger.warning("Run stopped on its spending limit at %s", self.spent)
        from langchain_core.messages import AIMessage

        return ModelResponse(result=[AIMessage(content=verdict.message)])

    def _note_warning(self, response: Any) -> None:
        """Put the warning on the turn, where somebody will read it."""
        said = self._to_say
        if said is None:
            verdict = self._cap.check(self.spent)
            if verdict is None or verdict.refuse:
                return
            said = verdict.message

        for message in reversed(getattr(response, "result", None) or []):
            carried = getattr(message, "additional_kwargs", None)
            if isinstance(carried, dict):
                carried["spend_warning"] = said
                self._to_say = None
                logger.info("Run spending warning: %s", said)
                return

        self._to_say = said

    def _account_for(self, response: Any) -> None:
        """Add the cost of `response` to the running total."""
        cost = _spent_on(response)
        if cost is None:
            self.unpriced_calls += 1
            return
        self.spent += cost
