"""A run that stopped for approval, answered to a caller with nobody at it."""

from __future__ import annotations

from typing import Any

FALLBACK_DECISIONS = ("approve", "reject")

KEYS = ("__interrupt__", "interrupts")


def paused_result(state: Any, *, thread_id: str) -> dict[str, Any] | None:
    """A structured pause, or None when the run actually finished."""
    if not isinstance(state, dict):
        return None

    waiting = next((state[key] for key in KEYS if state.get(key)), None)
    if not waiting:
        return None

    items = waiting if isinstance(waiting, list) else [{}]
    requests = [asked for item in items for asked in _requests(item)]

    return {
        "status": "needs_approval",
        "awaiting": requests or [_unnamed()],
        "resume": {
            "thread_id": thread_id,
            "decisions": _decisions(items),
        },
    }


def _requests(item: Any) -> list[dict[str, Any]]:
    """Every action one interrupt is waiting on."""
    value = item.get("value") if isinstance(item, dict) else None
    if not isinstance(value, dict):
        return []

    many = value.get("action_requests")
    if isinstance(many, list) and many:
        return [_asked(one) for one in many if isinstance(one, dict)]

    one = value.get("action_request")
    if not isinstance(one, dict):
        return []
    asked = _asked(one)
    if not asked["description"]:
        asked["description"] = str(value.get("description") or "")
    return [asked]


def _asked(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": str(request.get("name") or request.get("action") or "unknown"),
        "args": request.get("args") or {},
        "description": str(request.get("description") or ""),
    }


def _unnamed() -> dict[str, Any]:
    """A pause whose detail could not be read."""
    return {"action": "unknown", "args": {}, "description": ""}


def _decisions(items: list[Any]) -> list[str]:
    """What the agent says a caller may send back."""
    found: list[str] = []
    for item in items:
        value = item.get("value") if isinstance(item, dict) else None
        if not isinstance(value, dict):
            continue
        for config in value.get("review_configs") or []:
            if not isinstance(config, dict):
                continue
            for decision in config.get("allowed_decisions") or []:
                if decision not in found:
                    found.append(str(decision))
    return found or list(FALLBACK_DECISIONS)
