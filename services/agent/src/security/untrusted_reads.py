"""Whether this run has read anything from outside, and what to do about it."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from agent.src.security.taint import TaintLedger
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_READS: ContextVar[TaintLedger | None] = ContextVar("untrusted_reads", default=None)


def _ledger() -> TaintLedger:
    """The taint ledger for this context, made on first use."""
    found = _READS.get()
    if found is None:
        found = TaintLedger()
        _READS.set(found)
    return found


def forget_reads() -> None:
    """Start a run having read nothing."""
    _READS.set(None)


def note_untrusted_read(text: Any, *, source: str = "") -> None:
    """Remember that this run read something, and from where."""
    try:
        if isinstance(text, str) and text.strip():
            _ledger().record(text, source=source.strip())
    except Exception:
        logger.debug("Could not record an untrusted read", exc_info=True)


def sources_behind(answer: Any) -> tuple[str, ...]:
    """Which servers this answer repeats something from."""
    if not isinstance(answer, str) or not answer.strip():
        return ()
    found = _READS.get()
    if found is None:
        return ()
    try:
        return found.sources_for(answer)
    except Exception:
        logger.debug("Could not work out what an answer drew on", exc_info=True)
        return ()


def read_something_untrusted() -> bool:
    """Whether this context has read anything untrusted."""
    found = _READS.get()
    return bool(found and found.holds_anything())


def why_ask_before(tool: str, arguments: Any, *, writes: bool | None) -> str | None:
    """Why this call should be put to a person, or nothing."""
    if writes is False:
        return None
    if not read_something_untrusted():
        return None

    quoted = ""
    try:
        matched = _ledger().matched(arguments if isinstance(arguments, dict) else {})
        if matched:
            quoted = f" It repeats something that was read: {matched[0]}"
    except Exception:
        logger.debug("Could not compare arguments against what was read", exc_info=True)

    where = ""
    try:
        sources = _ledger().every_source()
        if sources:
            where = f" ({', '.join(sources)})"
    except Exception:
        logger.debug("Could not work out where the text was read from", exc_info=True)

    return (
        f"{tool} changes something, and this run has already read text from "
        f"outside the conversation{where}.{quoted}"
    )


def needs_a_question_here(
    tool: str, arguments: Any, *, writes: bool | None, policy: str
) -> str | None:
    """Whether *this layer* should raise the question, or leave it."""
    if policy != "allow":
        return None
    return why_ask_before(tool, arguments, writes=writes)


def question_payload(tool: str, arguments: Any, *, reason: str) -> dict[str, Any]:
    """The question, in the shape the approval surface renders."""
    return {
        "review_configs": [
            {
                "action_name": tool,
                "allowed_decisions": ["approve", "edit", "reject", "respond"],
            }
        ],
        "action_requests": [
            {
                "name": tool,
                "args": arguments if isinstance(arguments, dict) else {},
                "description": reason,
            }
        ],
    }
