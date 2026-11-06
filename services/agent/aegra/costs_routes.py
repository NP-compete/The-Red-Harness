"""What a month cost, and who should be billed for it."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/costs", tags=["costs"])

PENNY = Decimal("0.01")

_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


async def _who(request: Request) -> str:
    """The authenticated caller."""
    from agent.aegra.auth_helpers import authenticated_user_id

    return await authenticated_user_id(request, reject_anonymous=True)


async def _charges_in(month: str) -> dict[str, dict[str, Any]]:
    """The charges recorded for `month`, keyed by payer."""
    from agent.src.security.cost_attribution import charges_in

    return await charges_in(month)


async def _unpriced_in(month: str) -> int:
    """How many runs in `month` could not be priced."""
    from agent.src.security.cost_attribution import unpriced_in

    return await unpriced_in(month)


def _this_month() -> str:
    """The current month, as `YYYY-MM`."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


class ChargebackRowOut(BaseModel):
    """One payer's charges for the month."""

    payer: str
    amount: str
    runs: int


class ChargebackOut(BaseModel):
    """The month's chargeback, per payer and in total."""

    month: str
    currency: str = ""
    rate_card_version: str = ""
    rows: list[ChargebackRowOut] = []
    total: str = "0"
    unpriced_runs: int = 0
    complete: bool = True


@router.get("/chargeback", responses={200: {"model": ChargebackOut}})
async def chargeback(request: Request, month: str = "") -> dict[str, Any]:
    """Every payer's total for a month, largest first."""
    await _who(request)

    asked = month.strip() or _this_month()
    if not _MONTH.match(asked):
        raise HTTPException(
            status_code=422,
            detail=f"{asked!r} is not a month. Ask for one as 2026-03.",
        )

    found = await _charges_in(asked)

    rows = sorted(
        (
            {
                "payer": payer,
                "amount": str(entry["amount"]),
                "runs": entry["runs"],
            }
            for payer, entry in found.items()
        ),
        key=lambda row: Decimal(row["amount"]),
        reverse=True,
    )

    total = sum((entry["amount"] for entry in found.values()), Decimal("0"))

    from agent.aegra.rates_routes import rate_card

    card, _problem = rate_card()
    unpriced = await _unpriced_in(asked)
    return {
        "month": asked,
        "currency": settings.RATE_CARD_CURRENCY,
        "rate_card_version": card.version,
        "rows": rows,
        "total": str(total.quantize(PENNY)),
        "unpriced_runs": unpriced,
        "complete": unpriced == 0,
    }
