"""Every refusal names a code and says what to do about it.

This used to check a committed `contract/decisions.json` at the
repository root, which listed the outcomes, the refusal codes and a
remedy for each so another surface could read them without importing
Python. Nothing ever read it: no route served it, no document
mentioned it, and its remedies had already drifted from the code —
it said "connect the named system" where the resolver says "Connect
{target} and run this again."

A second, hand-maintained copy of an enum is a thing that goes out
of date silently. The check worth keeping was never about the file:
it is that a refusal a caller receives always carries a code they
can branch on and a remedy they can act on. That is asserted here
against the code itself, so there is nothing to keep in step.

If a consumer outside this repository ever needs the vocabulary,
serve it from the enums — `GET /contract/decisions` — rather than
committing a copy.
"""

from __future__ import annotations

import inspect
from typing import get_args

from agent.src.security import resolver
from agent.src.security.journal import Outcome
from agent.src.security.resolver import RefusalCode, Refused


def _refusals() -> list[RefusalCode]:
    """The codes `resolve` can actually return."""
    source = inspect.getsource(resolver)
    return [code for code in RefusalCode if f"RefusalCode.{code.name}" in source]


def test_there_are_codes_to_check():
    """An empty enum would pass everything below."""
    assert list(RefusalCode)


def test_every_code_is_reachable():
    """A code nothing returns is a branch a caller writes for nothing."""
    unreachable = sorted(set(RefusalCode) - set(_refusals()))
    assert not unreachable, (
        f"{[c.value for c in unreachable]} are declared and never returned. "
        "Return them or delete them; a published code that cannot happen is "
        "a caller handling a case that never arrives."
    )


def test_a_refusal_cannot_be_built_without_a_code_and_a_remedy():
    """Both are required, so no refusal reaches a caller missing one."""
    import pytest

    with pytest.raises(TypeError):
        Refused(code=RefusalCode.NO_AUTHORITY, message="no")  # no remedy
    with pytest.raises(TypeError):
        Refused(message="no", remedy="do this")  # no code


def test_no_refusal_is_built_without_one():
    """Every `Refused(...)` in the resolver passes a remedy."""
    source = inspect.getsource(resolver)
    built = source.count("Refused(")
    with_remedy = source.count("remedy=")
    assert built and with_remedy >= built - 1, (
        f"{built} Refused(...) constructed, {with_remedy} remedies given — "
        "a refusal without one says no and not what to do next"
    )


def test_the_outcomes_are_distinct():
    """Two outcomes sharing a value collapse into one for a caller.

    `Outcome` is a `Literal`, not an `Enum` — the deleted contract
    file listed these by hand, which is how it could carry four
    strings nothing checked against the type.
    """
    values = list(get_args(Outcome))
    assert values, "Outcome declares no values"
    assert len(values) == len(set(values)), f"duplicate outcome values: {values}"
