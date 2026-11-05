"""Three routes check thread ownership; they must answer alike."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

AEGRA = Path(__file__).resolve().parents[3] / "services" / "agent" / "aegra"

OWNERSHIP_CHECKERS = ("feedback.py", "eval_routes.py", "thread_cleanup.py")

RULE = re.compile(r"FROM thread\s+WHERE thread_id = %s AND user_id = %s", re.S)


def _source(name: str) -> str:
    return (AEGRA / name).read_text()


class TestTheRuleIsStillWrittenThreeTimes:
    """If this starts failing, the duplication was fixed — good."""

    @pytest.mark.parametrize("name", OWNERSHIP_CHECKERS)
    def test_the_module_still_checks_ownership(self, name: str):
        text = _source(name)
        assert RULE.search(text) or "AND user_id = %s" in text, (
            f"{name} no longer scopes a thread read to its owner. If that "
            "moved to a shared helper, update this file to follow it."
        )


class TestTheyAgreeOnTheAnswer:
    @pytest.mark.parametrize("name", OWNERSHIP_CHECKERS)
    def test_not_yours_is_not_announced_as_forbidden(self, name: str):
        text = _source(name)
        assert "Thread not owned by authenticated user" not in text, (
            f"{name} tells the caller the thread exists and belongs to "
            "somebody else. The other ownership checks answer 404, and so "
            "do the read-only write routes (CFG-10) and the gated analytics "
            "(PRIV-3)."
        )

    @pytest.mark.parametrize("name", OWNERSHIP_CHECKERS)
    def test_it_answers_not_found(self, name: str):
        assert "not found" in _source(name).lower(), name

    def test_the_outlier_is_gone_from_the_route_that_had_it(self):
        text = _source("eval_routes.py")
        assert "status_code=404, detail=f\"Thread '{thread_id}' not found\"" in text
        assert "Could not identify user from token" in text
