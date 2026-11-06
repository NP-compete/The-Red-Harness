"""Drive the configuration write surface against the running cluster."""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services"))

BASE = "http://localhost:8081"
HOST = "agent.localhost"
PATH = "config/agent/PROMPT.md"
MARK = "\n<!-- strand-C probe -->\n"


def call(method: str, route: str, body: dict | None = None) -> tuple[int, dict]:
    """Call the agent and return the status and decoded body."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + route, data=data, method=method)
    request.add_header("Host", HOST)
    if data:
        request.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as answer:
            return answer.status, json.loads(answer.read())
    except urllib.error.HTTPError as failed:
        return failed.code, json.loads(failed.read() or b"{}")


def roundtrips(name: str, model: type[BaseModel], body: dict) -> bool:
    """A schema that parses is not one that round-trips."""
    dumped = model.model_validate(body).model_dump(
        mode="json", by_alias=True, exclude_unset=True
    )
    if dumped == body:
        print(f"  {name:<22} round-trips")
        return True
    print(f"  {name:<22} DOES NOT round-trip", file=sys.stderr)
    print(f"    sent     {json.dumps(body)[:300]}", file=sys.stderr)
    print(f"    declared {json.dumps(dumped)[:300]}", file=sys.stderr)
    return False


def main() -> int:
    """Probe writing, reverting and reading back config files."""
    from agent.aegra.config_editing_routes import (
        AdoptBaselineOut,
        ConfigWrittenOut,
        DriftOut,
        HistoryOut,
    )

    code, current = call("GET", f"/config/file?path={PATH}")
    if code != 200:
        raise SystemExit(f"cannot read {PATH}: {code} {current}")
    version = current["version"]
    print(f"{PATH} is at version {version}")

    ok = True
    code, written = call(
        "PUT",
        "/config/edit",
        {"path": PATH, "content": current["content"] + MARK, "base_version": version},
    )
    if code != 200:
        raise SystemExit(f"edit refused: {code} {written}")
    print(f"edited to version {written['version']}, durable={written['durable']}")
    ok &= roundtrips("/config/edit", ConfigWrittenOut, written)

    code, read_back = call("GET", f"/config/file?path={PATH}")
    if not read_back["content"].endswith(MARK):
        raise SystemExit("the agent does not read back the edit it accepted")
    print("the agent reads the edit back")

    code, drift = call("GET", "/config/drift")
    paths = [one["path"] for one in drift["paths"]]
    if PATH not in paths:
        raise SystemExit(f"{PATH} is overridden and /config/drift does not say so")
    print(f"drift names it, {len(paths)} path(s) overridden")
    ok &= roundtrips("/config/drift", DriftOut, drift)

    code, history = call("GET", f"/config/history?path={PATH}")
    print(f"history has versions {[one['version'] for one in history['versions']]}")
    ok &= roundtrips("/config/history", HistoryOut, history)

    if len(history["versions"]) > 1:
        earlier = history["versions"][-2]["version"]
        code, reverted = call(
            "POST", "/config/revert", {"path": PATH, "version": earlier}
        )
        if code != 200:
            raise SystemExit(f"revert refused: {code} {reverted}")
        print(f"reverted to the content of version {earlier}")
        ok &= roundtrips("/config/revert", ConfigWrittenOut, reverted)

    code, dropped = call("POST", "/config/adopt-baseline", {"path": PATH})
    if code != 200:
        raise SystemExit(f"adopt-baseline refused: {code} {dropped}")
    print("override dropped")
    ok &= roundtrips("/config/adopt-baseline", AdoptBaselineOut, dropped)

    code, after = call("GET", "/config/drift")
    if PATH in [one["path"] for one in after["paths"]]:
        raise SystemExit("the override is still there after adopt-baseline")
    code, final = call("GET", f"/config/file?path={PATH}")
    if final["content"].endswith(MARK):
        raise SystemExit("the file still carries the probe's edit")
    print("the tree is back where it started")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
