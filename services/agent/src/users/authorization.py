"""Ask the policy whether this mutation is allowed (E9-T2)."""

from __future__ import annotations

from dataclasses import dataclass

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


@dataclass(frozen=True)
class Decision:
    """Whether a field class may be written, and why not."""

    allowed: bool
    reasons: list[str]
    field_class: str

    @property
    def why(self) -> str:
        """The reasons as one sentence."""
        return "; ".join(self.reasons) or "refused by policy"


async def decide(*, actor_role: str, target_role: str, field_class: str) -> Decision:
    """One class, one answer, from the policy engine."""
    import httpx

    from agent.src.opa.config import get_opa_timeout, get_opa_url

    payload = {
        "input": {
            "current_intent": {
                "action": "user_mutation",
                "actor_role": actor_role,
                "target_role": target_role,
                "field_class": field_class,
            }
        }
    }
    url = f"{get_opa_url().rstrip('/')}/deny_reasons"
    try:
        async with httpx.AsyncClient(timeout=get_opa_timeout()) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            reasons = response.json().get("result") or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("user mutation refused: policy engine unreachable: %s", exc)
        return Decision(
            allowed=False,
            reasons=[
                "the policy engine could not be reached, so the change was "
                "refused rather than allowed unchecked"
            ],
            field_class=field_class,
        )

    return Decision(
        allowed=not reasons,
        reasons=[str(r) for r in reasons],
        field_class=field_class,
    )


async def decide_all(
    *, actor_role: str, target_role: str, field_classes: list[str]
) -> list[Decision]:
    """Every class the request touches, asked separately."""
    return [
        await decide(actor_role=actor_role, target_role=target_role, field_class=one)
        for one in sorted(set(field_classes))
    ]
