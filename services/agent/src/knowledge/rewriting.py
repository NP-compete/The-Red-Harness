"""Rewriting a selected passage on request."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from agent.src.security.fencing import fence

_REQUEST = (
    "Rewrite the passage below as asked. Reply with only the rewritten "
    "passage — no preamble, no explanation, no quotation marks around it.\n\n"
    "What to do: {instruction}\n"
)

_ECHOED_FENCE = re.compile(r"<<<\s*external-content[^>]*>>>", re.IGNORECASE)


@dataclass(frozen=True)
class Rewritten:
    """The rewritten text, or the reason there is none."""

    ok: bool
    text: str = ""
    reason: str = ""


def rewrite_selection(
    selection: str,
    instruction: str,
    *,
    ask: Callable[[str], str],
) -> Rewritten:
    """Ask the model to rewrite `selection` as `instruction` says."""
    if not selection.strip():
        return Rewritten(False, reason="There is nothing selected to rewrite.")
    if not instruction.strip():
        return Rewritten(False, reason="Say what you would like changed.")

    prompt = _REQUEST.format(instruction=instruction.strip()) + fence(
        selection, source="a passage of your own note"
    )

    try:
        answer = ask(prompt)
    except Exception:
        return Rewritten(
            False,
            reason="The rewrite could not be done just now. Your text is unchanged.",
        )

    text = _ECHOED_FENCE.sub("", answer or "").strip()
    if not text:
        return Rewritten(
            False,
            reason="Nothing came back from the rewrite. Your text is unchanged.",
        )
    return Rewritten(True, text=text)
