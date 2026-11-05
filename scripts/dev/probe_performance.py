"""Take the NFR-PERF numbers off the running cluster."""

from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services"))

BASE = "http://localhost:8081"
HOST = "agent.localhost"
NAMESPACE = "template-agent"

unmeasured: dict[str, str] = {}
results: list[tuple[str, str, str, bool | None]] = []


def report(req: str, took: str, target: str, met: bool | None) -> None:
    """Record one measurement against its target."""
    results.append((req, took, target, met))


def call(
    method: str, route: str, body: dict | None = None, timeout: int = 180
) -> tuple[int, Any]:
    """Make an HTTP call to the agent and return the status and decoded body."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + route, data=data, method=method)
    request.add_header("Host", HOST)
    if data:
        request.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            raw = answer.read()
            return answer.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as failed:
        raw = failed.read()
        try:
            return failed.code, json.loads(raw)
        except Exception:
            return failed.code, {"body": raw.decode(errors="replace")[:200]}


def sh(command: str) -> str:
    # Developer-only probe; every call site passes a literal command built
    # from constants in this file, never from user input.
    """Run a shell command and return its stdout, stripped."""
    return subprocess.run(  # nosec B602  # noqa: S602
        command, shell=True, capture_output=True, text=True
    ).stdout.strip()


def p95(values: list[float]) -> float:
    """The 95th percentile, or the worst sample when there are few."""
    if len(values) < 20:
        return max(values)
    return statistics.quantiles(values, n=20)[-1]


def agent_pod() -> str:
    """The name of the agent pod, or an empty string if there is none."""
    return sh(
        f"kubectl -n {NAMESPACE} get pod -l component=agent "
        "-o jsonpath='{.items[0].metadata.name}'"
    )


def readiness() -> None:
    """Measure how long the agent pod took to become ready (PERF-5)."""
    pod = agent_pod()
    if not pod:
        unmeasured["PERF-5"] = "no agent pod"
        return
    raw = sh(f"kubectl -n {NAMESPACE} get pod {pod} -o json")
    if not raw:
        unmeasured["PERF-5"] = "could not read the pod"
        return
    from datetime import datetime

    body = json.loads(raw)

    def when(stamp: str) -> datetime:
        """Parse a Kubernetes timestamp."""
        return datetime.fromisoformat(stamp.replace("Z", "+00:00"))

    conditions = {
        c["type"]: c["lastTransitionTime"] for c in body["status"]["conditions"]
    }
    started = body["status"]["containerStatuses"][0]["state"]["running"]["startedAt"]
    took = (when(conditions["Ready"]) - when(started)).total_seconds()

    container = [c for c in body["spec"]["containers"] if c["name"] == "agent"][0]
    delay = (container.get("readinessProbe") or {}).get("initialDelaySeconds", 0)
    report("PERF-5 readiness after container start", f"{took:.1f}s", "< 20s", took < 20)
    print(
        f"    the floor is the probe, not the app: readinessProbe "
        f"initialDelaySeconds={delay}s, and the app reports its own startup "
        "complete in under 2s"
    )


def graph_build() -> None:
    """Measure graph build time from the agent's logs (PERF-3)."""
    pod = agent_pod()
    lines = sh(
        f"kubectl -n {NAMESPACE} logs {pod} --tail=4000 2>/dev/null "
        "| grep -o 'Graph built in [0-9]*ms'"
    )
    built = [float(one.split()[3].rstrip("ms")) for one in lines.splitlines() if one]
    if not built:
        unmeasured["PERF-2"] = (
            "no 'Graph built in …' line in the pod's log. The agent may not "
            "have missed its cache since it started — drive a run on a new "
            "user, or restart the pod first"
        )
        return
    worst = p95([v / 1000 for v in built])
    report(
        f"PERF-2 graph build on a cache miss ({len(built)} sample(s))",
        f"{worst:.2f}s",
        "< 3s",
        worst < 3,
    )


def mcp_discovery() -> None:
    """Measure how long MCP server discovery takes (PERF-4)."""
    took: list[float] = []
    for _ in range(10):
        start = time.monotonic()
        code, _ = call("GET", "/mcp/servers", timeout=60)
        if code != 200:
            unmeasured["PERF-4"] = f"/mcp/servers answered {code}"
            return
        took.append(time.monotonic() - start)
    warm = took[1:]
    worst = p95(warm)
    report(
        f"PERF-4 MCP tool discovery, cached ({len(warm)} sample(s))",
        f"{worst * 1000:.0f}ms",
        "< 200ms",
        worst < 0.2,
    )
    print(f"    cold first call: {took[0] * 1000:.0f}ms")


def first_token() -> None:
    """Measure time to first streamed token (PERF-1)."""
    code, thread = call("POST", "/threads", {"metadata": {"title": "perf probe"}})
    if code not in (200, 201):
        unmeasured["PERF-1"] = f"could not open a thread: {code}"
        return
    thread_id = thread["thread_id"]
    took: list[float] = []
    for _ in range(5):
        body = json.dumps(
            {
                "assistant_id": "agent",
                "input": {"messages": [{"role": "user", "content": "say pong"}]},
                "stream_mode": ["messages"],
            }
        ).encode()
        request = urllib.request.Request(
            f"{BASE}/threads/{thread_id}/runs/stream", data=body, method="POST"
        )
        request.add_header("Host", HOST)
        request.add_header("content-type", "application/json")
        start = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=300) as stream:
                event = b""
                for line in stream:
                    if line.startswith(b"event:"):
                        event = line.strip()
                    if line.startswith(b"data:") and event and b"metadata" not in event:
                        took.append(time.monotonic() - start)
                        break
        except Exception as failed:  # noqa: BLE001
            unmeasured["PERF-1"] = f"the stream failed: {failed}"
            return
    if not took:
        unmeasured["PERF-1"] = "no data frame arrived"
        return
    worst = p95(took)
    report(
        f"PERF-1 end to end, first token ({len(took)} sample(s))",
        f"{worst:.2f}s",
        "< 1.5s",
        None,
    )
    print(
        f"    samples: {', '.join(f'{v:.1f}s' for v in took)}"
        "\n    NOT the requirement: PERF-1 excludes provider latency and "
        "this is dominated by it. The split is below."
    )
    _harness_side(thread_id)


def _harness_side(thread_id: str) -> None:
    """The part of PERF-1 the requirement is actually about."""
    pod = agent_pod()
    raw = sh(
        f"kubectl -n {NAMESPACE} logs {pod} --tail=4000 2>/dev/null "
        f"| grep -F {thread_id}"
    )
    picked: dict[str, str] = {}
    prompted: dict[str, str] = {}
    tokens: dict[str, int] = {}
    for line in raw.splitlines():
        stamp = re.search(r"(\d\d:\d\d:\d\d\.\d+)Z", line)
        run = re.search(
            r"run_id\x1b?\[?[0-9;]*m?=\x1b?\[?[0-9;]*m?([0-9a-f-]{36})", line
        )
        if not stamp or not run:
            continue
        if "Worker picked up run" in line:
            picked.setdefault(run.group(1), stamp.group(1))
        if "prompt_size" in line:
            prompted.setdefault(run.group(1), stamp.group(1))
            count = re.search(
                r"approx_tokens\x1b?\[?[0-9;]*m?=\x1b?\[?[0-9;]*m?(\d+)", line
            )
            if count:
                tokens[run.group(1)] = int(count.group(1))

    def seconds(value: str) -> float:
        """Parse an `HH:MM:SS.sss` span into seconds."""
        hours, minutes, rest = value.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(rest)

    spans = [
        seconds(prompted[run]) - seconds(picked[run])
        for run in picked
        if run in prompted
    ]
    if spans:
        worst = p95(spans)
        report(
            f"PERF-1 harness only, accepted to model call ({len(spans)})",
            f"{worst * 1000:.0f}ms",
            "< 1.5s",
            worst < 1.5,
        )
    else:
        unmeasured["PERF-1 split"] = (
            "no matching 'Worker picked up run' and 'prompt_size' pair in the "
            "pod log for this thread"
        )

    if tokens:
        worst_prompt = max(tokens.values())
        report(
            f"PERF-3 prompt on a trivial turn ({len(tokens)} sample(s))",
            f"{worst_prompt} tok",
            "< 3,000",
            worst_prompt < 3000,
        )
        print(
            "    approx_tokens from the `prompt_size` middleware, on a "
            "turn whose user message is eight characters"
        )
    else:
        unmeasured["PERF-3"] = "no prompt_size line found for this thread"
    call("DELETE", f"/threads/{thread_id}")


def search() -> None:
    """Measure search latency against the database (PERF-2)."""
    pg = sh(
        f"kubectl -n {NAMESPACE} get pod -l component=database "
        "-o jsonpath='{.items[0].metadata.name}'"
    )
    rows = (
        sh(
            f"kubectl -n {NAMESPACE} exec {pg} -- psql -U postgres -d template_agent "
            '-tAc "select count(*) from thread"'
        )
        if pg
        else ""
    )
    took: list[float] = []
    for _ in range(10):
        start = time.monotonic()
        code, _ = call("GET", "/search/threads?q=pong", timeout=60)
        if code != 200:
            unmeasured["PERF-6"] = f"/search answered {code}"
            return
        took.append(time.monotonic() - start)
    worst = p95(took)
    report(
        f"PERF-6 search over threads ({rows or '?'} rows, not 100k)",
        f"{worst * 1000:.0f}ms",
        "< 500ms at 100k rows",
        worst < 0.5,
    )
    print(
        f"    the target is at 100,000 rows and this cluster holds {rows or '?'}. "
        "A fast answer over a small table says nothing about the plan at scale"
    )


def main() -> int:
    """Run every probe and print the results."""
    print("NFR-PERF, measured against the running cluster\n")
    for step in (readiness, graph_build, mcp_discovery, first_token, search):
        try:
            step()
        except Exception as failed:  # noqa: BLE001
            unmeasured[step.__name__] = f"the probe itself failed: {failed}"

    print()
    for req, took, target, met in results:
        mark = "ok  " if met else ("MISS" if met is False else "    ")
        print(f"  {mark} {req:<52} {took:>8}  target {target}")

    print("\nnot measured here:")
    for req, why in (
        unmeasured
        | {
            "PERF-7": (
                "no sync I/O on the request path. This is asyncio debug mode "
                "over the test suite plus review, not a number"
            ),
        }
    ).items():
        print(f"  {req:<10} {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
