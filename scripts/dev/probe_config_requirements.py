"""NFR-CFG, asked of the running deployment."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services"))

BASE = "http://localhost:8081"
HOST = "agent.localhost"
AGENT_YAML = "config/agent/runtime/agent.yaml"

ELSEWHERE = {
    "CFG-1": "every capability reachable from config — a claim about the whole "
    "surface, not a question a request can answer",
    "CFG-2": "both layouts resolve through one helper — "
    "tests/unit/config/ drives the resolver directly",
    "CFG-3": "safe defaults — the registry half is `make feature-registry`; "
    "the rest is per-setting and read in review",
    "CFG-5": "the reference is generated — `make config-reference` then a diff; "
    "nothing in CI checks it is current yet",
    "CFG-6": "caches keyed on config invalidate — the overlay half is "
    "tests/unit/config/test_store_is_installed_for_reads.py; the others are "
    "not audited",
    "CFG-10 (read-only)": "the write routes are not registered — needs a "
    "deployment in readonly, so "
    "tests/unit/config/test_readonly_registers_no_writer.py asks the router "
    "instead. Verified by hand against this cluster by patching "
    "`UI_CONFIG_MODE` in the agent-config ConfigMap: all four writers 404",
}

failures: list[str] = []


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


def check(requirement: str, held: bool, saying: str) -> None:
    """Print one requirement's result and record a failure."""
    print(f"  {'ok  ' if held else 'FAIL'}  {requirement:<8} {saying}")
    if not held:
        failures.append(requirement)


def cfg4_and_9() -> None:
    """Validation refuses, and refuses without applying anything."""
    code, current = call("GET", f"/config/file?path={AGENT_YAML}")
    if code != 200:
        raise SystemExit(f"cannot read {AGENT_YAML}: {code} {current}")
    text = current["content"]
    version = current["version"]

    typo = text.replace("knowledge:", "knowledg:\nknowledge:", 1)
    code, _ = call(
        "PUT",
        "/config/edit",
        {"path": AGENT_YAML, "content": typo, "base_version": version},
    )
    check("CFG-4", code == 422, f"a mistyped section is refused ({code})")

    mistyped = text.replace(
        "knowledge:\n  enabled: false", 'knowledge:\n  enabled: "false"', 1
    )
    code, _ = call(
        "PUT",
        "/config/edit",
        {"path": AGENT_YAML, "content": mistyped, "base_version": version},
    )
    check("CFG-4", code == 422, f"a quoted boolean is refused ({code})")

    code, drift = call("GET", "/config/drift")
    check(
        "CFG-9",
        not drift["paths"],
        "a refused edit applied nothing",
    )

    good = text + "\n# probe\n"
    code, written = call(
        "PUT",
        "/config/edit",
        {"path": AGENT_YAML, "content": good, "base_version": version},
    )
    check("CFG-9", code == 200, f"a sound edit is accepted ({code})")
    if code == 200:
        check(
            "CFG-9",
            written["version"] > version,
            f"and versioned ({version} -> {written['version']})",
        )
        code, history = call("GET", f"/config/history?path={AGENT_YAML}")
        check("CFG-9", code == 200 and bool(history["versions"]), "and in the history")
        code, _ = call("POST", "/config/adopt-baseline", {"path": AGENT_YAML})
        check("CFG-9", code == 200, "and revertible")
        code, drift = call("GET", "/config/drift")
        check("CFG-9", not drift["paths"], "the tree is back where it started")


def cfg8() -> None:
    """A flag's declared scope is enforced, not documented."""
    code, _ = call("POST", "/features/not_a_flag", {"enabled": True})
    check("CFG-8", code == 404, f"an undeclared flag is refused ({code})")

    code, said = call("POST", "/features/planner_enabled", {"enabled": True})
    check("CFG-8", code == 409, f"a flag set at another level is refused ({code})")
    if code == 409:
        check(
            "CFG-8",
            "agent level" in json.dumps(said),
            "and says which level decides",
        )

    code, said = call("POST", "/features/browser_automation_enabled", {"enabled": True})
    check(
        "CFG-8",
        code == 409 and "sandbox_backend" in json.dumps(said),
        f"a missing precondition is named, not guessed at ({code})",
    )

    code, listed = call("GET", "/features")
    hidden = [one for one in listed["features"] if one.get("ui_exposed") is False]
    if hidden:
        name = hidden[0]["key"]
        code, _ = call("POST", f"/features/{name}", {"enabled": True})
        check("CFG-8", code == 404, f"a hidden flag is not reachable by URL ({code})")
    else:
        print(
            "  --    CFG-8    every declared flag is ui_exposed here, so the "
            "hidden-flag branch is unexercised (the handler refuses it with 404)"
        )


def cfg10_writable() -> None:
    """The mode is not writable through any API."""
    code, editing = call("GET", "/config/editing")
    check("CFG-10", code == 200, f"the mode is reported ({editing['mode']})")

    code, _ = call(
        "PUT",
        "/config/edit",
        {"path": "config/agent/runtime/ui.yaml", "content": "x", "base_version": 0},
    )
    check("CFG-10", code != 200, f"a path outside the allowlist is refused ({code})")


def main() -> int:
    """Check the NFR-CFG requirements against the running deployment."""
    print("NFR-CFG, against the running deployment")
    cfg4_and_9()
    cfg8()
    cfg10_writable()

    if failures:
        print(f"\n{len(set(failures))} requirement(s) do not hold", file=sys.stderr)
        return 1
    print("\nevery requirement checked here holds")
    print("\nnot asked of the deployment:")
    for requirement, why in ELSEWHERE.items():
        print(f"  {requirement:<18} {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
