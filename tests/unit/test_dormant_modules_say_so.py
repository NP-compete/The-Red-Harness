"""A module that describes a job it is not doing."""

from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2] / "services" / "agent"

DORMANT = [
    "aegra/state.py",
    "aegra/nodes.py",
    "aegra/converters.py",
    "aegra/serialization.py",
]


def _docstring(relative: str) -> str:
    import ast

    tree = ast.parse((ROOT / relative).read_text())
    return (ast.get_docstring(tree) or "").lower()


@pytest.mark.parametrize("relative", DORMANT)
def test_it_is_still_dormant(relative):
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from test_unreachable_modules import unreachable

    assert relative in {str(p) for p in unreachable()}


@pytest.mark.parametrize("relative", DORMANT)
def test_it_says_nothing_is_calling_it(relative):
    said = _docstring(relative)
    assert "not currently" in said or "nothing imports" in said or "dormant" in said


@pytest.mark.parametrize("relative", DORMANT)
def test_it_still_explains_what_it_is_for(relative):
    assert len(_docstring(relative)) > 120
