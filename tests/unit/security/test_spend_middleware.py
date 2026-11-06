"""Counting what a run has spent, as it spends it."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.src.security.spend_middleware import SpendLimitMiddleware, _spent_on


def usage(inp: int, out: int) -> SimpleNamespace:
    message = SimpleNamespace(
        usage_metadata={"input_tokens": inp, "output_tokens": out}
    )
    return SimpleNamespace(result=[message])


class TestReadingWhatACallUsed:
    def test_prices_a_call_from_its_usage(self):
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.25", "currency": "USD"},
        ):
            assert _spent_on(usage(100, 50)) == Decimal("0.25")

    def test_a_call_that_reported_no_usage_costs_nothing_known(self):
        assert _spent_on(SimpleNamespace(result=[SimpleNamespace()])) is None

    def test_an_unpriced_call_is_unknown_rather_than_free(self):
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": None, "currency": "USD"},
        ):
            assert _spent_on(usage(100, 50)) is None

    def test_a_response_with_no_messages_is_unknown(self):
        assert _spent_on(SimpleNamespace(result=[])) is None


class TestTheRunningTotal:
    @staticmethod
    def _middleware(**caps) -> SpendLimitMiddleware:
        return SpendLimitMiddleware(
            warn_at=caps.get("warn_at"), refuse_at=caps.get("refuse_at")
        )

    @pytest.mark.asyncio
    async def test_a_cheap_run_is_left_alone(self):
        mw = self._middleware(refuse_at=Decimal("1.00"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.01", "currency": "USD"},
        ):
            out = await mw.awrap_model_call(object(), lambda _r: _answer())
        assert out is not None

    @pytest.mark.asyncio
    async def test_the_total_adds_up_across_calls(self):
        mw = self._middleware(refuse_at=Decimal("1.00"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.40", "currency": "USD"},
        ):
            await mw.awrap_model_call(object(), lambda _r: _answer())
            await mw.awrap_model_call(object(), lambda _r: _answer())
        assert mw.spent == Decimal("0.80")

    @pytest.mark.asyncio
    async def test_the_run_is_stopped_once_it_has_passed_the_ceiling(self):
        """On the next call: a call already made cannot be unmade."""
        mw = self._middleware(refuse_at=Decimal("0.50"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            await mw.awrap_model_call(object(), lambda _r: _answer())
            stopped = await mw.awrap_model_call(object(), lambda _r: _answer())
        said = " ".join(str(getattr(m, "content", "")) for m in stopped.result)
        assert "0.50" in said

    @pytest.mark.asyncio
    async def test_a_deployment_with_no_ceiling_never_stops(self):
        mw = self._middleware()
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "99.00", "currency": "USD"},
        ):
            out = await mw.awrap_model_call(object(), lambda _r: _answer())
        assert out is not None


async def _answer():
    return usage(100, 50)


class TestWhenTheCheckHappens:
    """Before the call, not after it."""

    @pytest.mark.asyncio
    async def test_a_run_already_over_the_ceiling_makes_no_further_call(self):
        mw = SpendLimitMiddleware(refuse_at=Decimal("0.50"))
        calls = []

        async def handler(_request):
            calls.append(1)
            return usage(100, 50)

        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            await mw.awrap_model_call(object(), handler)
            await mw.awrap_model_call(object(), handler)

        assert len(calls) == 1, "the second call should not have been made"

    @pytest.mark.asyncio
    async def test_the_first_call_is_always_allowed(self):
        """Nothing has been spent yet, so nothing can be over."""
        mw = SpendLimitMiddleware(refuse_at=Decimal("0.00001"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "1.00", "currency": "USD"},
        ):
            assert await mw.awrap_model_call(object(), lambda _r: _answer()) is not None


class TestTheRefusalReachesThePerson:
    """Raising inside the middleware stopped the spending and nothing else."""

    @staticmethod
    def _text(response) -> str:
        return " ".join(str(getattr(m, "content", "")) for m in response.result)

    @pytest.mark.asyncio
    async def test_the_refused_call_answers_instead_of_vanishing(self):
        mw = SpendLimitMiddleware(refuse_at=Decimal("0.50"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            await mw.awrap_model_call(object(), lambda _r: _answer())
            out = await mw.awrap_model_call(object(), lambda _r: _answer())
        assert out is not None and out.result

    @pytest.mark.asyncio
    async def test_the_answer_says_the_limit_was_reached(self):
        mw = SpendLimitMiddleware(refuse_at=Decimal("0.50"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            await mw.awrap_model_call(object(), lambda _r: _answer())
            out = await mw.awrap_model_call(object(), lambda _r: _answer())
        assert "spending limit" in self._text(out).lower()

    @pytest.mark.asyncio
    async def test_the_answer_names_the_ceiling(self):
        mw = SpendLimitMiddleware(refuse_at=Decimal("0.50"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            await mw.awrap_model_call(object(), lambda _r: _answer())
            out = await mw.awrap_model_call(object(), lambda _r: _answer())
        assert "0.50" in self._text(out)

    @pytest.mark.asyncio
    async def test_no_further_call_is_made(self):
        mw = SpendLimitMiddleware(refuse_at=Decimal("0.50"))
        calls = []

        async def handler(_request):
            calls.append(1)
            return usage(100, 50)

        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            await mw.awrap_model_call(object(), handler)
            await mw.awrap_model_call(object(), handler)
        assert len(calls) == 1


class TestTheTallyBelongsToOneRun:
    """The middleware is built once per graph and reused for every run."""

    @pytest.mark.asyncio
    async def test_a_new_run_starts_from_nothing(self):
        mw = SpendLimitMiddleware(refuse_at=Decimal("0.50"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            await mw.awrap_model_call(object(), lambda _r: _answer())
        assert mw.spent == Decimal("0.60")

        mw.before_agent({}, None)
        assert mw.spent == Decimal("0")

    @pytest.mark.asyncio
    async def test_a_new_run_is_not_refused_for_the_last_one(self):
        mw = SpendLimitMiddleware(refuse_at=Decimal("0.50"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            await mw.awrap_model_call(object(), lambda _r: _answer())
            mw.before_agent({}, None)
            calls = []

            async def handler(_request):
                calls.append(1)
                return usage(100, 50)

            await mw.awrap_model_call(object(), handler)
        assert len(calls) == 1, "the new run should have been allowed to call"

    def test_the_warning_is_said_again_in_a_new_run(self):
        mw = SpendLimitMiddleware(warn_at=Decimal("0.10"), refuse_at=Decimal("1.00"))
        mw.spent = Decimal("0.20")
        assert mw._refusal() is None
        mw.before_agent({}, None)
        mw.spent = Decimal("0.20")
        assert mw._refusal() is None
        assert mw._cap._warned is True, "a fresh run warns on its own crossing"


def _kwargs(response) -> dict:
    return getattr(response.result[-1], "additional_kwargs", {}) or {}


def speaking(inp: int = 100, out: int = 50):
    """A model reply the way one actually arrives, with somewhere to"""

    async def answer(_request=None):
        message = SimpleNamespace(
            usage_metadata={"input_tokens": inp, "output_tokens": out},
            additional_kwargs={},
            content="here you go",
        )
        return SimpleNamespace(result=[message])

    return answer


class TestTheWarningReachesThePerson:
    """A warning written only to the log is not a warning."""

    @staticmethod
    def _middleware(**caps) -> SpendLimitMiddleware:
        return SpendLimitMiddleware(
            warn_at=caps.get("warn_at"),
            refuse_at=caps.get("refuse_at"),
            currency=caps.get("currency", "USD"),
        )

    @pytest.mark.asyncio
    async def test_the_turn_carries_the_warning(self):
        mw = self._middleware(warn_at=Decimal("0.50"), refuse_at=Decimal("1.00"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            out = await mw.awrap_model_call(object(), speaking())
        assert "spend_warning" in _kwargs(out)

    @pytest.mark.asyncio
    async def test_the_warning_says_what_has_been_spent(self):
        mw = self._middleware(warn_at=Decimal("0.50"), refuse_at=Decimal("1.00"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            out = await mw.awrap_model_call(object(), speaking())
        assert "0.60" in _kwargs(out)["spend_warning"]

    @pytest.mark.asyncio
    async def test_the_warning_says_what_the_figure_is_in(self):
        mw = self._middleware(
            warn_at=Decimal("0.50"), refuse_at=Decimal("1.00"), currency="EUR"
        )
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "EUR"},
        ):
            out = await mw.awrap_model_call(object(), speaking())
        assert "EUR" in _kwargs(out)["spend_warning"]

    @pytest.mark.asyncio
    async def test_a_run_under_the_threshold_is_told_nothing(self):
        mw = self._middleware(warn_at=Decimal("0.50"), refuse_at=Decimal("1.00"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.01", "currency": "USD"},
        ):
            out = await mw.awrap_model_call(object(), speaking())
        assert "spend_warning" not in _kwargs(out)

    @pytest.mark.asyncio
    async def test_it_is_said_once_and_not_on_every_call_after(self):
        mw = self._middleware(warn_at=Decimal("0.50"), refuse_at=Decimal("9.00"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            first = await mw.awrap_model_call(object(), speaking())
            second = await mw.awrap_model_call(object(), speaking())
        assert "spend_warning" in _kwargs(first)
        assert "spend_warning" not in _kwargs(second)

    @pytest.mark.asyncio
    async def test_the_next_run_can_be_warned_again(self):
        mw = self._middleware(warn_at=Decimal("0.50"), refuse_at=Decimal("9.00"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            await mw.awrap_model_call(object(), speaking())
            await mw.abefore_agent({})
            again = await mw.awrap_model_call(object(), speaking())
        assert "spend_warning" in _kwargs(again)

    @pytest.mark.asyncio
    async def test_the_refusal_still_names_the_currency(self):
        mw = self._middleware(refuse_at=Decimal("0.50"), currency="GBP")
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "GBP"},
        ):
            await mw.awrap_model_call(object(), speaking())
            stopped = await mw.awrap_model_call(object(), speaking())
        said = " ".join(str(getattr(m, "content", "")) for m in stopped.result)
        assert "GBP" in said

    @pytest.mark.asyncio
    async def test_a_reply_with_nowhere_to_put_it_still_comes_back(self):
        mw = self._middleware(warn_at=Decimal("0.50"), refuse_at=Decimal("1.00"))
        with patch(
            "agent.aegra.rates_routes.price_tokens",
            return_value={"cost": "0.60", "currency": "USD"},
        ):
            out = await mw.awrap_model_call(object(), lambda _r: _answer())
        assert out is not None
