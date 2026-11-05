"""Running a suite against a local agent."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

_SERVICES = str(REPO_ROOT / "services")
if _SERVICES not in sys.path:
    sys.path.insert(0, _SERVICES)

from scripts.bench.guard import BenchRefused, check_safe_to_run  # noqa: E402


def _agent_url() -> str:
    """Where the agent is, from the environment or the local default."""
    return f"http://127.0.0.1:{os.getenv('AGENT_PORT', '5002')}"


def _effects_of(url: str) -> str:
    """What the agent says it may change, or nothing if it will not say."""
    import httpx

    try:
        found = httpx.get(f"{url}/admin/config", timeout=10)
        if found.status_code != 200:
            return ""
        return str((found.json().get("execution") or {}).get("effects") or "")
    except Exception:
        return ""


def _model_of(url: str) -> str:
    """Which model this agent actually answers with."""
    import httpx

    try:
        found = httpx.get(f"{url}/config/settings", timeout=10)
        if found.status_code == 200:
            settings = _flatten(found.json())
            override = settings.get("MODEL_OVERRIDE") or ""
            if override:
                return str(override)
    except Exception:
        pass

    try:
        found = httpx.get(f"{url}/admin/config", timeout=10)
        if found.status_code != 200:
            return ""
        return str((found.json().get("agent") or {}).get("model") or "")
    except Exception:
        return ""


def _flatten(payload: Any) -> dict[str, Any]:
    """Every `{name, value}` the settings view reports, by name."""
    found: dict[str, Any] = {}

    def walk(node: Any) -> None:
        """Collect every name/value pair reachable in the payload."""
        if isinstance(node, dict):
            if "name" in node and "value" in node:
                found[str(node["name"])] = node.get("value")
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    return found


def main(argv: list[str] | None = None) -> int:
    """Run a benchmark suite against the agent."""
    parser = argparse.ArgumentParser(prog="bench")
    parser.add_argument("--suite", required=True)
    parser.add_argument("--results", default="data/bench/results.jsonl")
    parser.add_argument(
        "--check",
        action="store_true",
        help="only report whether a run is possible, and why not",
    )
    args = parser.parse_args(argv)

    url = _agent_url()
    effects = _effects_of(url)

    if args.check:
        try:
            check_safe_to_run(effects=effects)
        except BenchRefused as refused:
            print(f"Refusing to run: {refused}", file=sys.stderr)
            return 2
        print(f"The agent at {url} is safe to measure against.")
        return 0

    from scripts.bench.preflight import preflight

    checks = preflight(suite=args.suite, url=url, effects=effects, model=_model_of(url))
    for check in checks:
        print(check, file=sys.stderr)

    missing = [one for one in checks if not one.ok]
    if not missing:
        return 0

    print(
        f"\n{len(missing)} prerequisite(s) unmet — nothing was run. See docs/development/bench.md.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
