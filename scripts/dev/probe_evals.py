"""Drive the /evals management routes against the running cluster."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services"))

BASE = "http://localhost:8081"
HOST = "agent.localhost"

failures: list[str] = []

CASES = [
    {
        "id": "strand-c-probe-1",
        "query": "what is this probe for",
        "expected_response": "checking the declared shape",
        "expected_keywords": ["shape"],
    },
    {
        "id": "strand-c-probe-2",
        "query": "and the second one",
        "expected_intent": "coverage",
        "expected_tool_calls": [],
    },
]


def call(method: str, route: str, body: dict | None = None) -> tuple[int, Any]:
    """Call the agent and return the status and decoded body."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + route, data=data, method=method)
    request.add_header("Host", HOST)
    if data:
        request.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as answer:
            raw = answer.read()
            return answer.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as failed:
        raw = failed.read()
        return failed.code, (json.loads(raw) if raw else None)


def roundtrips(name: str, model: type[BaseModel], body: Any) -> None:
    """Report whether `body` survives a round trip through `model`."""
    dumped = model.model_validate(body).model_dump(
        mode="json", by_alias=True, exclude_unset=True
    )
    if dumped == body:
        print(f"  {name:<30} round-trips")
        return
    failures.append(name)
    print(f"  {name:<30} DOES NOT round-trip", file=sys.stderr)
    print(f"    sent     {json.dumps(body)[:300]}", file=sys.stderr)
    print(f"    declared {json.dumps(dumped)[:300]}", file=sys.stderr)


def main() -> int:
    """Probe the eval dataset, drift, history and model routes."""
    from agent.aegra.eval_routes import (
        DatasetUpsertedOut,
        EvalDatasetOut,
        EvalDriftOut,
        EvalHistoryOut,
        EvalModelsOut,
        EvalRecordOut,
        EvalTrendsOut,
    )

    print("/evals, read-only")
    for route, model in (
        ("/evals/status", EvalRecordOut),
        ("/evals/history", EvalHistoryOut),
        ("/evals/trends", EvalTrendsOut),
        ("/evals/drift", EvalDriftOut),
        ("/evals/models", EvalModelsOut),
    ):
        code, body = call("GET", route)
        if code != 200:
            raise SystemExit(f"{route}: {code} {body}")
        roundtrips(f"GET  {route}", model, body)

    code, body = call("GET", "/evals/history?limit=5")
    roundtrips("GET  /evals/history?limit=5", EvalHistoryOut, body)
    code, body = call("GET", "/evals/drift?baseline=0.5&limit=3")
    roundtrips("GET  /evals/drift?baseline", EvalDriftOut, body)

    print("/evals/dataset, with content in it")
    code, before = call("GET", "/evals/dataset")
    if code != 200:
        raise SystemExit(f"cannot read the dataset: {code} {before}")
    had = before["dataset"]["cases"]
    judge = before["judge_model"]
    print(f"  the deployment has {len(had)} case(s); putting two of mine in")

    try:
        code, stored = call(
            "POST", "/evals/dataset", {"cases": CASES, "judge_model": "probe-judge"}
        )
        if code != 200:
            raise SystemExit(f"dataset refused: {code} {stored}")
        roundtrips("POST /evals/dataset", DatasetUpsertedOut, stored)
        if stored["case_count"] != len(CASES):
            raise SystemExit(
                f"sent {len(CASES)} cases and the deployment stored "
                f"{stored['case_count']}"
            )

        code, read_back = call("GET", "/evals/dataset")
        cases = read_back["dataset"]["cases"]
        if [one.get("id") for one in cases] != [one["id"] for one in CASES]:
            raise SystemExit(f"the dataset read back is not the one sent: {cases}")
        if read_back["judge_model"] != "probe-judge":
            raise SystemExit("the judge model did not survive the round trip")
        roundtrips("GET  /evals/dataset (2 cases)", EvalDatasetOut, read_back)
    finally:
        call("POST", "/evals/dataset", {"cases": had, "judge_model": judge})
        code, after = call("GET", "/evals/dataset")
        restored = after["dataset"]["cases"]
        if restored != had:
            print(
                f"  WARNING: the dataset was not restored — had {len(had)}, "
                f"now {len(restored)}",
                file=sys.stderr,
            )
        else:
            print(f"  dataset restored to its {len(had)} original case(s)")

    if failures:
        print(
            f"\n{len(failures)} response(s) do not match the declared shape",
            file=sys.stderr,
        )
        return 1
    print("\nevery response checked matches the shape its route declares")
    print("not checked, no eval runner here: /trigger, /force-trigger,")
    print("/results, /results/export")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
