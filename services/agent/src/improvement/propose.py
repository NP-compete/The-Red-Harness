"""Refusing a proposed change that would remove a control."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

_PERMISSIVENESS = {"deny": 0, "ask": 1, "allow": 2}

_APPROVAL_MODES = {"all": 0, "selected": 1, "none": 2}

_APPROVAL = "human_approval"
_TRUSTED_SERVERS = "trusted_servers"
_FENCE = "tool_output.fence"
_CAPS = ("daily_spend", "monthly_spend", "max_bytes", "run_limit", "spend_limit")


@dataclass(frozen=True)
class Verdict:
    """Whether a change may be put to a reviewer, and why not."""

    permitted: bool
    reason: str = ""


def may_propose(*, before: Any, after: Any) -> Verdict:
    """Whether this change may be put in front of a reviewer."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return Verdict(False, "a proposal has to be two sets of settings")

    objections: list[str] = []
    for key, old, new in _leaves(before, after):
        complaint = _objection(key, old, new)
        if complaint:
            objections.append(complaint)

    if not objections:
        return Verdict(True)

    return Verdict(False, "; ".join(objections))


def _leaves(before: Any, after: Any, *, prefix: str = "") -> list[tuple[str, Any, Any]]:
    """Every setting in either side, by dotted name, with both values."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return [(prefix, before, after)]

    found: list[tuple[str, Any, Any]] = []
    for key in sorted(set(before) | set(after)):
        name = f"{prefix}.{key}" if prefix else str(key)
        old, new = before.get(key), after.get(key)
        if isinstance(old, dict) and isinstance(new, dict):
            found.extend(_leaves(old, new, prefix=name))
        else:
            found.append((name, old, new))
    return found


def _objection(key: str, old: Any, new: Any) -> str:
    """The objection to this key changing, or an empty string."""
    if old == new:
        return ""
    if _APPROVAL in key:
        return _approval_objection(key, old, new)
    if _TRUSTED_SERVERS in key:
        return _trust_objection(key, old, new)
    if key == _FENCE:
        return _fence_objection(key, old, new)
    if any(name in key for name in _CAPS):
        return _cap_objection(key, old, new)
    return ""


def _approval_objection(key: str, old: Any, new: Any) -> str:
    """The objection to an approval rule changing."""
    if old is None:
        return ""
    if new is None:
        return f"{key} removes the {old!s} rule"

    leaf = key.rsplit(".", 1)[-1]
    if leaf == "enabled":
        return f"{key} turns tool approval off" if _true(old) and not _true(new) else ""
    if leaf == "mode":
        was, now = _APPROVAL_MODES.get(str(old)), _APPROVAL_MODES.get(str(new))
        if was is None or now is None:
            return f"{key} changes a decision this cannot read: {old!s} to {new!s}"
        return f"{key} widens {old!s} to {new!s}" if now > was else ""
    if leaf == "exclude":
        added = _names(new) - _names(old)
        return f"{key} stops asking before {', '.join(sorted(added))}" if added else ""

    was, now = _PERMISSIVENESS.get(str(old)), _PERMISSIVENESS.get(str(new))
    if was is None or now is None:
        return f"{key} changes a decision this cannot read: {old!s} to {new!s}"
    return f"{key} widens {old!s} to {new!s}" if now > was else ""


def _trust_objection(key: str, old: Any, new: Any) -> str:
    """The objection to vouching for more servers."""
    added = _names(new) - _names(old)
    return f"{key} vouches for {', '.join(sorted(added))}" if added else ""


def _fence_objection(key: str, old: Any, new: Any) -> str:
    """The objection to no longer fencing what a server returns."""
    if str(old).lower() == "true" and str(new).lower() != "true":
        return f"{key} stops fencing what comes back from a server"
    return ""


def _cap_objection(key: str, old: Any, new: Any) -> str:
    """The objection to a limit being raised or removed."""
    if old is None:
        return ""
    if new is None:
        return f"{key} removes a limit"
    try:
        return (
            f"{key} raises {old!s} to {new!s}"
            if Decimal(str(new)) > Decimal(str(old))
            else ""
        )
    except (InvalidOperation, ValueError):
        return f"{key} changes a limit this cannot read: {old!s} to {new!s}"


def _true(value: Any) -> bool:
    """Whether `value` reads as true."""
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def _names(value: Any) -> set[str]:
    """`value` as a set of names, however it was written."""
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    return {part.strip() for part in str(value or "").split(",") if part.strip()}
