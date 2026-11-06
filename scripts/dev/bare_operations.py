"""How many operations still return an undescribed object (E10 strand C)."""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "tests/fixtures/openapi-baseline.json"

METHODS = ("get", "post", "put", "patch", "delete")

UPSTREAM = frozenset(
    {
        "GET /",
        "GET /live",
        "GET /ready",
        "DELETE /threads/{thread_id}",
        "POST /threads/{thread_id}/commands",
        "POST /threads/{thread_id}/runs/stream",
        "POST /threads/{thread_id}/runs/wait",
        "GET /threads/{thread_id}/runs/{run_id}/join",
        "GET /threads/{thread_id}/runs/{run_id}/stream",
        "POST /assistants/count",
        "DELETE /assistants/{assistant_id}",
        "GET /assistants/{assistant_id}/graph",
        "GET /assistants/{assistant_id}/subgraphs",
        "POST /runs/crons/count",
        "POST /runs/stream",
        "POST /runs/wait",
    }
)


def _declared(response: dict) -> bool:
    """Whether this response says what it sends."""
    schema = ((response.get("content") or {}).get("application/json") or {}).get(
        "schema"
    )
    if not schema:
        return False
    if "$ref" in schema or "allOf" in schema or "anyOf" in schema:
        return True
    return bool(schema.get("properties") or schema.get("items") or schema.get("enum"))


def bare(include_upstream: bool = False) -> dict[str, list[str]]:
    """Every operation in the baseline with no response model, grouped by path."""
    paths = json.loads(BASELINE.read_text())["paths"]
    found: dict[str, list[str]] = collections.defaultdict(list)
    for path, operations in sorted(paths.items()):
        for method, operation in operations.items():
            if method not in METHODS:
                continue
            responses = operation.get("responses") or {}
            success = [code for code in responses if code.startswith("2")]
            if success and all(
                not (responses[code].get("content")) for code in success
            ):
                continue
            if any(_declared(responses[code]) for code in success):
                continue
            if any(
                (responses[code].get("content") or {})
                and "application/json" not in (responses[code].get("content") or {})
                for code in success
            ):
                continue
            if not include_upstream and f"{method.upper()} {path}" in UPSTREAM:
                continue
            found["/" + path.strip("/").split("/")[0]].append(
                f"{method.upper():6} {path}"
            )
    return found


def total() -> int:
    """How many operations the baseline describes."""
    paths = json.loads(BASELINE.read_text())["paths"]
    return sum(
        1 for operations in paths.values() for method in operations if method in METHODS
    )


def main(argv: list[str]) -> int:
    """Report the operations still missing a response model."""
    include_upstream = "--upstream" in argv
    argv = [one for one in argv if one != "--upstream"]
    found = bare(include_upstream=include_upstream)
    count = sum(len(one) for one in found.values())
    if argv:
        group = argv[0] if argv[0].startswith("/") else "/" + argv[0]
        for one in found.get(group, []):
            print(one)
        print(f"\n{len(found.get(group, []))} bare in {group}")
        return 0
    for group, operations in sorted(found.items(), key=lambda kv: -len(kv[1])):
        print(f"  {group:<22} {len(operations)}")
    print(f"\n{count} of {total()} operations return an undescribed object")
    if not include_upstream:
        print(
            f"{len(UPSTREAM)} more do, and are aegra_api's rather than this "
            "repository's — `--upstream` to list them"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
