#!/usr/bin/env python
"""Run AppWorld tasks against this harness.

    benchmarks/.venv/bin/python benchmarks/appworld/runner.py --split dev --limit 5

One task is one conversation, so no task can see another's
history — the same isolation `scripts/bench` relies on. The loop
is AppWorld's: the agent writes Python, this executes it in the
task's world, the output goes back as the next turn, and the
agent stops by calling `apis.supervisor.complete_task(...)`.

**Nothing here scores anything.** AppWorld's own evaluator does,
on world state, and this records what it said. An adapter that
graded itself would be measuring its own opinion.

**Read `--help` on `--split` before quoting a number.** `train`
and `dev` are for development; `test_normal` and `test_challenge`
are the splits the leaderboard reports, and running those
repeatedly while tuning a prompt is how a test set stops being
one.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
# This directory, not `benchmarks/`. Adding the parent would put a
# directory called `appworld` on the path ahead of the installed
# package of that name, and every `import appworld` below would
# then find this adapter instead of the benchmark.
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from protocol import ProtocolError, code_in, conversation  # noqa: E402

#: Where `appworld download data` put its world.
#:
#: AppWorld resolves `data/` and `experiments/` against the current
#: working directory, so without this the runner only works when
#: invoked from `benchmarks/` and reports "The task directory
#: doesn't exist" from anywhere else. Pinned to this checkout so
#: the command in the README works from the repository root, which
#: is where every other command here is run from.
APPWORLD_ROOT = Path(os.environ.get("APPWORLD_ROOT", HERE.parent))

AGENT = os.environ.get("BENCH_AGENT_URL", "http://agent.localhost:8081")
AGENT_HOST = os.environ.get("BENCH_AGENT_HOST", "")
USER = os.environ.get("BENCH_USER", "appworld-bench")


@dataclass
class Outcome:
    """How one benchmark task went."""

    task_id: str
    steps: int
    seconds: float
    completed: bool
    passed: bool | None
    error: str


def _headers() -> dict[str, str]:
    """The headers every request to the agent carries."""
    headers = {"Content-Type": "application/json", "X-User-Id": USER}
    if AGENT_HOST:
        headers["Host"] = AGENT_HOST
    return headers


def _call(path: str, body: dict, timeout: int) -> dict:
    """POST `body` to `path` on the agent and return the decoded reply."""
    request = urllib.request.Request(
        f"{AGENT}{path}",
        method="POST",
        data=json.dumps(body).encode(),
        headers=_headers(),
    )
    with urllib.request.urlopen(request, timeout=timeout) as answer:
        parsed: dict = json.load(answer)
    return parsed


def _text(payload: dict) -> str:
    """The assistant's reply, whatever shape the content came in."""
    messages = payload.get("messages") or []
    if not messages:
        return ""
    content = messages[-1].get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return str(content or "")


def _ask(thread_id: str, message: list[dict] | str, wall: int) -> str:
    """One turn. A list is sent as-is; a string is one human turn."""
    messages = (
        message
        if isinstance(message, list)
        else [{"role": "human", "content": message}]
    )
    payload = _call(
        f"/threads/{thread_id}/runs/wait",
        {"assistant_id": "agent", "input": {"messages": messages}},
        timeout=wall,
    )
    return _text(payload)


def _attempt(job: tuple[str, int, int, str]) -> "Outcome":
    """One task, never raising.

    Module level and taking a single tuple, because a worker
    process receives this by pickle: a closure over `main`'s
    arguments fails with "Can't get local object
    'main.<locals>.attempt'" the moment it is submitted.
    """
    task_id, steps, wall, experiment = job
    try:
        return run_task(task_id, steps=steps, wall=wall, experiment=experiment)
    except Exception as broke:  # noqa: BLE001
        # Recorded and carried on. One unreachable agent, one
        # malformed response or one bad task is not a reason to
        # discard the rest of the split.
        return Outcome(task_id, 0, 0.0, False, None, f"runner: {broke}")


def _child(root: str) -> None:
    """Point a worker process at the same world the parent uses.

    Spawned children re-import this module but do not inherit the
    parent's `update_root`, so without this each one resolves
    `data/` against its own working directory and reports that the
    task directory does not exist.
    """
    import appworld

    appworld.update_root(root)


def run_task(task_id: str, *, steps: int, wall: int, experiment: str) -> Outcome:
    """One task, start to score."""
    from appworld import AppWorld

    started = time.time()
    with AppWorld(task_id=task_id, experiment_name=experiment) as world:
        who = world.task.supervisor
        supervisor = {
            key: getattr(who, key, "")
            for key in ("first_name", "last_name", "email", "phone_number")
        }
        apps = world.execute("print(apis.api_docs.show_app_descriptions())")

        try:
            turns = conversation(world.task.instruction, supervisor, apps)
        except ProtocolError as refused:
            return Outcome(task_id, 0, 0.0, False, None, str(refused))

        thread_id = _call("/threads", {"metadata": {"appworld_task": task_id}}, 60)[
            "thread_id"
        ]

        # Their few-shot dialogue goes in as *turns*, not as one
        # labelled blob.
        #
        # Flattening it into "User: ... Assistant: ..." was the
        # first thing this runner did, and the agent answered every
        # task with `complete_task(status="fail")` on step two: a
        # wall of text containing a finished worked example reads
        # as a transcript to observe rather than a conversation to
        # continue. Sent as alternating roles, the model is the
        # assistant mid-dialogue, which is what their baseline does.
        opening = [{"role": turn.role, "content": turn.content} for turn in turns]

        taken, error = 0, ""
        message: list[dict] | str = opening
        for taken in range(1, steps + 1):
            try:
                reply = _ask(thread_id, message, wall)
            except (
                urllib.error.URLError,
                http.client.HTTPException,
                TimeoutError,
                OSError,
            ) as failed:
                error = f"agent unreachable: {failed}"
                break

            try:
                code = code_in(reply)
            except ProtocolError:
                # Not a failure of the task: the agent said something
                # without code. Ask once more, with the rule restated.
                message = (
                    "Reply with a single ```python block to run next, or call "
                    "apis.supervisor.complete_task(...) if you are done."
                )
                continue

            output = world.execute(code)
            if world.task_completed():
                break
            message = output

        # Their evaluator, on world state. Never ours.
        completed = world.task_completed()
        passed: bool | None
        try:
            report = world.evaluate()
            passed = bool(
                getattr(report, "success", None) or report.to_dict().get("success")
            )
        except Exception as unscored:  # noqa: BLE001
            passed, error = None, error or f"evaluator: {unscored}"

    return Outcome(
        task_id=task_id,
        steps=taken,
        seconds=round(time.time() - started, 1),
        completed=completed,
        passed=passed,
        error=error,
    )


def main() -> int:
    """Run the AppWorld benchmark over a split."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split",
        default="dev",
        choices=("train", "dev", "test_normal", "test_challenge"),
        help="test_normal and test_challenge are what the leaderboard reports",
    )
    parser.add_argument("--limit", type=int, default=0, help="first N tasks, 0 for all")
    parser.add_argument("--steps", type=int, default=30, help="REPL turns per task")
    parser.add_argument("--wall", type=int, default=300, help="seconds per agent turn")
    parser.add_argument("--experiment", default="harness", help="AppWorld run name")
    parser.add_argument("--out", default="", help="write results as JSONL here")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="tasks in parallel. A turn is ~10s of model call, so this is "
        "the only real speedup; too many and the agent's one replica "
        "becomes the bottleneck instead of the provider",
    )
    args = parser.parse_args()

    import appworld

    appworld.update_root(str(APPWORLD_ROOT))
    if not (APPWORLD_ROOT / "data" / "tasks").is_dir():
        print(
            f"No AppWorld data under {APPWORLD_ROOT}. Run:\n"
            f"  cd {APPWORLD_ROOT} && .venv/bin/appworld install "
            f"&& .venv/bin/appworld download data",
            file=sys.stderr,
        )
        return 1

    task_ids = appworld.load_task_ids(args.split)
    if args.limit:
        task_ids = task_ids[: args.limit]

    print(
        f"appworld: {len(task_ids)} task(s) from {args.split} "
        f"against {AGENT} as {USER}",
        file=sys.stderr,
    )

    # Written as they finish, not at the end.
    #
    # A 57-task run is over an hour, and the first version kept
    # everything in memory until the last task: an IncompleteRead
    # from the agent on task 37 killed the process and took 36
    # completed, paid-for results with it. Appending means a crash
    # costs the task it happened on.
    out = Path(args.out) if args.out else None
    if out:
        out.write_text("")

    # Consecutive unreachable-agent results, and the point at which
    # carrying on stops being useful.
    #
    # The first full run recorded twenty 503s in a row after the pod
    # was OOMKilled, and AppWorld scored every one of them as a
    # zero — a 59.7 that described a dead backend rather than an
    # agent. Twenty consecutive failures to reach the server is not
    # a benchmark result; it is a reason to stop and say so.
    GIVE_UP_AFTER = 5
    unreachable = 0

    class BackendGone(RuntimeError):
        """The agent stopped answering; the rest would be noise."""

    results: list[Outcome] = []
    # One lock for the file. Threads finish out of order and a
    # half-written line is a results file nobody can parse.
    writing = threading.Lock()

    def record(outcome: Outcome, index: int) -> None:
        """Record one task's outcome and print its mark."""
        results.append(outcome)
        if out:
            with writing, out.open("a") as handle:
                handle.write(json.dumps(asdict(outcome)) + "\n")
        mark = (
            "pass" if outcome.passed else ("fail" if outcome.passed is False else "?")
        )
        print(
            f"  [{index}/{len(task_ids)}] {outcome.task_id:<16} {mark:<5} "
            f"{outcome.steps:>3} steps {outcome.seconds:>6.1f}s {outcome.error[:50]}",
            file=sys.stderr,
        )

    def watch(outcome: Outcome) -> None:
        """Count unreachable results, and stop once it is hopeless."""
        nonlocal unreachable
        # Structural, not a string match. The first version of this
        # looked for "unreachable" or "503" in the error and missed
        # a refused connection entirely, because that arrives as
        # `runner: <urlopen error [Errno 61] Connection refused>`.
        # A task that took zero steps and could not be scored never
        # reached the agent at all, whatever the wording.
        if outcome.passed is None and outcome.steps == 0:
            unreachable += 1
            if unreachable >= GIVE_UP_AFTER:
                raise BackendGone(
                    f"{unreachable} tasks in a row produced no steps at all. "
                    "Stopping: the rest would be scored as zeros. The last "
                    f"error was: {outcome.error}\n"
                    "  If it names a connection or a 503, the agent is "
                    "down — check `kubectl get pods`; it has been OOMKilled "
                    "before. Any other error is this runner's own."
                )
        else:
            unreachable = 0

    if args.workers > 1:
        # Processes, not threads.
        #
        # Threads were the obvious choice — the work is waiting on
        # HTTP — and every task failed instantly with "SQLite
        # objects created in a thread can only be used in that same
        # thread". AppWorld's worlds hold SQLite connections with
        # thread affinity, which is why their own runner takes
        # `--num-processes` rather than threads.
        done = 0
        try:
            with ProcessPoolExecutor(
                max_workers=args.workers,
                initializer=_child,
                initargs=(str(APPWORLD_ROOT),),
            ) as pool:
                futures = {
                    pool.submit(
                        _attempt, (tid, args.steps, args.wall, args.experiment)
                    ): tid
                    for tid in task_ids
                }
                for future in as_completed(futures):
                    done += 1
                    outcome = future.result()
                    record(outcome, done)
                    watch(outcome)
        except BackendGone as gone:
            print(f"\nappworld: {gone}", file=sys.stderr)
            return 1
    else:
        for index, task_id in enumerate(task_ids, 1):
            outcome = _attempt((task_id, args.steps, args.wall, args.experiment))
            record(outcome, index)
            try:
                watch(outcome)
            except BackendGone as gone:
                print(f"\nappworld: {gone}", file=sys.stderr)
                return 1
        mark = (
            "pass" if outcome.passed else ("fail" if outcome.passed is False else "?")
        )
        print(
            f"  [{index}/{len(task_ids)}] {task_id:<16} {mark:<5} "
            f"{outcome.steps:>3} steps {outcome.seconds:>6.1f}s {outcome.error[:50]}",
            file=sys.stderr,
        )

    # Their aggregate, not ours.
    #
    # AppWorld reports Task Goal Completion and Scenario Goal
    # Completion, and `evaluate_tasks` is what computes them. A
    # pass count of our own would be a third number that looks
    # like theirs and is not comparable to anything published.
    scored = [r for r in results if r.passed is not None]
    try:
        report = appworld.evaluate_tasks(
            [r.task_id for r in results], experiment_name=args.experiment
        )
        aggregate = (report.to_dict() if hasattr(report, "to_dict") else report).get(
            "aggregate", {}
        )
    except Exception as unscored:  # noqa: BLE001
        aggregate = {}
        print(f"\nappworld: could not aggregate: {unscored}", file=sys.stderr)

    print(f"\nappworld {args.split} ({len(results)} task(s)):", file=sys.stderr)
    for metric, value in aggregate.items():
        print(f"  {metric:<26} {value}", file=sys.stderr)
    if len(scored) != len(results):
        print(
            f"  {len(results) - len(scored)} task(s) could not be scored",
            file=sys.stderr,
        )

    if args.limit:
        # SGC is defined over every variation of a scenario. A
        # limited run takes the first N task ids, which cuts
        # scenarios in half, so the SGC above describes whatever
        # fragment happened to be included.
        print(
            "\n  NOTE: --limit was used. task_goal_completion is over the tasks run;\n"
            "  scenario_goal_completion needs every variation of each scenario and\n"
            "  is not comparable to a published figure from a partial split.",
            file=sys.stderr,
        )

    if out:
        print(f"appworld: wrote {out}", file=sys.stderr)

    # Non-zero only when nothing could be scored: a low score is a
    # result, not a failure of the run.
    return 0 if scored else 1


if __name__ == "__main__":
    raise SystemExit(main())
