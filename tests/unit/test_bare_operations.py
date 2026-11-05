"""The list of operations excused as upstream is checked, not trusted."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/dev"))

from bare_operations import UPSTREAM, bare, total  # noqa: E402

BASELINE = ROOT / "tests/fixtures/openapi-baseline.json"

AEGRA_TAGS = {
    "Assistants",
    "Crons",
    "Event Streaming",
    "Health",
    "Stateless Runs",
    "Store",
    "Thread Runs",
    "Threads",
}


def _operation(entry: str) -> dict:
    method, path = entry.split(" ", 1)
    paths = json.loads(BASELINE.read_text())["paths"]
    assert path in paths, f"{entry} names a path the baseline does not have"
    assert method.lower() in paths[path], f"{entry} names a method that path lacks"
    return paths[path][method.lower()]


class TestTheExemptionsAreReal:
    @pytest.mark.parametrize("entry", sorted(UPSTREAM))
    def test_each_one_is_declared_upstream(self, entry):
        """Not just absent from here — present there."""
        operation = _operation(entry)
        tags = set(operation.get("tags") or [])
        if entry == "GET /":
            assert operation.get("operationId", "").startswith("root_handler")
            return
        assert tags & AEGRA_TAGS, (
            f"{entry} is excused as aegra_api's and carries {sorted(tags)}, "
            "which is not one of aegra's. Either it moved into this "
            "repository and needs a response shape, or the entry is wrong."
        )

    def test_the_duplicate_delete_is_still_aegras(self):
        """`DELETE /threads/{thread_id}` exists here *and* upstream."""
        operation = _operation("DELETE /threads/{thread_id}")
        assert operation.get("tags") == ["Threads"], (
            "the contract's delete-thread operation is no longer aegra's. If "
            "this repository's handler now wins, it needs a response shape."
        )

    def test_every_exemption_is_actually_bare(self):
        """A declared operation does not need an excuse."""
        listed = {
            line.strip()
            for group in bare(include_upstream=True).values()
            for line in group
        }
        normalised = {" ".join(one.split()) for one in listed}
        for entry in sorted(UPSTREAM):
            assert entry in normalised, (
                f"{entry} is on the upstream list and is not bare. Remove it: "
                "the list exists to explain what is left, not to pad it."
            )


class TestTheCountItself:
    def test_nothing_of_ours_is_undeclared(self):
        """What the PRD claims, as an assertion."""
        left = bare()
        assert not left, (
            "these operations return an undescribed object and are ours: "
            f"{json.dumps({k: v for k, v in left.items()}, indent=1)}"
        )

    def test_the_baseline_has_operations_in_it(self):
        assert total() > 100
