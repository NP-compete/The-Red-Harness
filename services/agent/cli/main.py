"""The command line."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Callable

from agent.cli import inventory as inventory_ops
from agent.cli import observe as observe_ops
from agent.cli import runs as run_ops
from agent.cli import threads as thread_ops
from agent.cli.ask import AskFailed, ask
from agent.cli.doctor import DEGRADED_EXIT, as_json, diagnose, exit_code
from agent.cli.inventory import InventoryFailed
from agent.cli.observe import ObserveFailed
from agent.cli.reference import SHELLS
from agent.cli.resume import DECISIONS, ResumeFailed, resume_run
from agent.cli.runs import RunFailed
from agent.cli.threads import ThreadFailed
from agent.cli.transport import Unauthenticated

USAGE_ERROR = 2

UNAUTHENTICATED = 4

SERVE_ROLES = ("agent", "ui", "all", "worker", "eval-worker", "opa", "acp")

NEEDS_DECISION = 3

NOISY = ("httpx", "httpcore", "urllib3")


def quieten_libraries() -> None:
    """Keep library chatter out of the output."""
    import logging

    for name in NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)


def _probe_world() -> dict[str, Any]:
    """What is actually true of this deployment."""
    import os

    from agent.cli.probes import (
        agent_reachable,
        config_clean,
        config_readable,
        model_key_present,
        override_store_available,
        tracing_configured,
        versions_agree,
        within_limits,
    )

    base = os.environ.get("HARNESS_URL", "http://localhost:5002")
    world = {
        "agent_reachable": agent_reachable(base),
        "config_readable": config_readable(),
        "model_key_present": model_key_present(),
        "override_store": override_store_available(),
        "tracing_configured": tracing_configured(),
    }
    for name, answer in (
        ("versions_agree", versions_agree(base)),
        ("config_clean", config_clean(base)),
        ("within_limits", within_limits(base)),
    ):
        if answer is not None:
            world[name] = answer
    return world


def _report(findings: list[Any]) -> str:
    if not findings:
        return "Nothing to report. This deployment looks usable."
    lines = []
    for found in findings:
        lines.append(f"[{found.severity.name.lower()}] {found.name}: {found.detail}")
        lines.append(f"  -> {found.remedy}")
    return "\n".join(lines)


def _default_asker(question: str, *, follow: bool = False, **kwargs: Any) -> Any:
    """Ask, waiting or watching."""
    import sys

    from agent.cli.transport import HttpTransport

    transport = HttpTransport(_base_url())
    if not follow:
        return ask(question, transport=transport, **kwargs)

    from agent.cli.ask import ask_following

    def _write(piece: str) -> None:
        sys.stdout.write(piece)
        sys.stdout.flush()

    answer = ask_following(question, transport=transport, write=_write, **kwargs)
    sys.stdout.write("\n")
    return _Printed(answer)


class _Printed:
    """An answer whose text has already reached the terminal."""

    def __init__(self, answer: Any) -> None:
        self.text = ""
        self.thread_id = answer.thread_id
        self.paused = answer.paused
        self.streamed_text = answer.text


def _base_url() -> str:
    import os

    return os.environ.get("HARNESS_URL", "http://localhost:5002")


def build_parser() -> argparse.ArgumentParser:
    """Every command, as a parser and nothing else."""
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Talk to an agent, and find out why it is not working.",
        epilog=(
            "exit codes: 0 it worked, 1 it did not, "
            f"{USAGE_ERROR} used wrongly, {NEEDS_DECISION} it is "
            f"waiting for a decision, {UNAUTHENTICATED} it does not know "
            f"who you are, {DEGRADED_EXIT} it worked but something is "
            "missing"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    from agent.version import version as _version

    parser.add_argument(
        "--version",
        action="version",
        version=f"harness {_version()}",
        help="which build this is — the same number the agent reports",
    )
    sub = parser.add_subparsers(dest="command")

    for role, what in (
        ("agent", "serve the agent API"),
        ("ui", "serve the built interface and its BFF"),
        (
            "all",
            "serve every enabled role under one supervisor — Kind and demos, not production",
        ),
        ("worker", "serve the background worker"),
        ("opa", "serve the policy engine from the config tree"),
        ("eval-worker", "run queued evaluations"),
        ("acp", "serve the ACP surface"),
    ):
        serving = sub.add_parser(role, help=what)
        serving.add_argument(
            "--ui-dir", default=None, help="where the interface is built"
        )

    finishing = sub.add_parser(
        "completion", help="a completion script for your shell (E28-T12)"
    )
    finishing.add_argument("shell", choices=list(SHELLS))

    sub.add_parser("docs", help="the command reference, as markdown")

    doctor = sub.add_parser("doctor", help="what is misconfigured, and the fix")
    doctor.add_argument("--json", action="store_true", help="machine-readable output")

    question = sub.add_parser("ask", help="ask one question and wait for the answer")
    question.add_argument("question", help="what to ask")
    question.add_argument(
        "--approve-all",
        action="store_true",
        help=(
            "answer every approval with yes, without asking. Each one is "
            "printed; an approval gate nobody sees open is not a gate"
        ),
    )
    question.add_argument(
        "--follow",
        action="store_true",
        help="print the answer as it arrives, rather than when it is finished",
    )
    question.add_argument("--json", action="store_true", help="machine-readable output")

    machine = argparse.ArgumentParser(add_help=False)
    machine.add_argument("--json", action="store_true", help="machine-readable output")

    conversation = sub.add_parser("thread", parents=[machine], help="conversations")
    thread_actions = conversation.add_subparsers(dest="action")
    thread_actions.add_parser(
        "list", parents=[machine], help="every conversation you can see"
    )
    for name, helptext in (
        ("show", "what a conversation holds"),
        ("rm", "remove a conversation"),
        ("fork", "copy a conversation into a new one"),
    ):
        one = thread_actions.add_parser(name, parents=[machine], help=helptext)
        one.add_argument("thread_id")

    settings = sub.add_parser(
        "config", parents=[machine], help="the configuration tree this agent reads"
    )
    doing_config = settings.add_subparsers(dest="action")
    doing_config.add_parser(
        "list", parents=[machine], help="every file, and whether it may be changed"
    )
    showing = doing_config.add_parser(
        "show", parents=[machine], help="one file as the agent reads it now"
    )
    showing.add_argument("path")
    doing_config.add_parser(
        "diff",
        parents=[machine],
        help="what this deployment reads that its tree does not say",
    )
    rendering = doing_config.add_parser(
        "render",
        parents=[machine],
        help="write the tree as the agent currently reads it",
    )
    rendering.add_argument("--out", required=True, help="a directory to write into")
    writing = doing_config.add_parser(
        "set", parents=[machine], help="replace one file, from a file or from stdin"
    )
    writing.add_argument("path")
    writing.add_argument(
        "--from",
        dest="source",
        default="-",
        help="where the new text comes from; '-' is stdin, the default",
    )
    writing.add_argument(
        "--force",
        action="store_true",
        help="write without the version it was read at, overwriting whatever is there",
    )

    execution = sub.add_parser("run", parents=[machine], help="runs on a conversation")
    doing = execution.add_subparsers(dest="action")
    listing = doing.add_parser(
        "list", parents=[machine], help="every run on a conversation"
    )
    listing.add_argument("thread_id")
    for name, helptext in (("show", "one run in full"), ("cancel", "stop a run")):
        one = doing.add_parser(name, parents=[machine], help=helptext)
        one.add_argument("thread_id")
        one.add_argument("run_id")
    rejoining = doing.add_parser(
        "attach", parents=[machine], help="pick up a run whose connection dropped"
    )
    rejoining.add_argument("thread_id")
    rejoining.add_argument("run_id")
    rejoining.add_argument(
        "--follow", action="store_true", help="watch the rest of it arrive"
    )

    checking = sub.add_parser(
        "eval", parents=[machine], help="what this deployment checks, and how it scores"
    )
    doing_evals = checking.add_subparsers(dest="action")
    doing_evals.add_parser(
        "list", parents=[machine], help="every check this deployment declares"
    )
    doing_evals.add_parser(
        "usage", parents=[machine], help="which checks have actually run"
    )
    scoring = doing_evals.add_parser(
        "run", parents=[machine], help="run one retrieval check now"
    )
    scoring.add_argument("check")

    servers = sub.add_parser("mcp", parents=[machine], help="integrations")
    server_actions = servers.add_subparsers(dest="action")
    server_actions.add_parser(
        "list", parents=[machine], help="which integrations this agent can use"
    )
    connecting = server_actions.add_parser(
        "connect", parents=[machine], help="start an integration's sign-in"
    )
    connecting.add_argument("name")
    connecting.add_argument(
        "--open",
        action="store_true",
        help="open the authorize URL in a browser",
    )
    connecting.add_argument(
        "--wait",
        type=int,
        default=0,
        metavar="SECONDS",
        help="poll until it connects, then say who as",
    )
    checking = server_actions.add_parser(
        "status", parents=[machine], help="whether one integration is usable now"
    )
    checking.add_argument("name")
    dropping = server_actions.add_parser(
        "disconnect", parents=[machine], help="forget this account's token"
    )
    dropping.add_argument("name")

    skills = sub.add_parser(
        "skill", parents=[machine], help="what the agent knows how to do"
    )
    skills.add_subparsers(dest="action").add_parser(
        "list", parents=[machine], help="every skill the agent has"
    )

    looking = sub.add_parser(
        "observe",
        parents=[machine],
        help="what the agent's own runs suggest looking at",
    )
    looking.add_argument("--limit", type=int, default=100, help="conversations to read")
    looking.add_argument(
        "--since", default=None, help="ignore anything older (ISO date)"
    )
    looking.add_argument(
        "--propose",
        action="store_true",
        help="also say what could be changed, as a diff somebody reviews",
    )
    looking.add_argument(
        "--max", type=int, default=0, help="how many proposals at most"
    )

    proposing = sub.add_parser(
        "propose",
        parents=[machine],
        help="whether a configuration change may be proposed",
    )
    proposing.add_argument("--before", required=True, help="settings as they are")
    proposing.add_argument("--after", required=True, help="settings as proposed")

    answering = sub.add_parser(
        "resume", parents=[machine], help="answer a run that stopped for a decision"
    )
    answering.add_argument("thread_id")
    answering.add_argument("decision", choices=list(DECISIONS))
    answering.add_argument("--message", default="", help="why, for a rejection")

    return parser


def _dispatch(
    argv: list[str] | None = None,
    *,
    probes: Callable[[], dict[str, Any]] = _probe_world,
    asker: Callable[..., Any] = _default_asker,
    threads: Any = thread_ops,
    runs: Any = run_ops,
    inventory: Any = inventory_ops,
    observer: Any = observe_ops,
    resumer: Any = resume_run,
) -> int:
    parser = build_parser()

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.command is None:
        parser.print_help(sys.stdout)
        return USAGE_ERROR

    if args.command in ("completion", "docs"):
        from agent.cli.reference import completion, reference

        print(
            completion(args.shell, parser)
            if args.command == "completion"
            else reference(parser),
            end="",
        )
        return 0

    if args.command in SERVE_ROLES:
        from agent.cli.serve import serve

        return serve(args.command, ui_dir=args.ui_dir)

    if args.command == "ask":
        return _ask(args, asker)

    if args.command == "thread":
        return _thread(args, threads, parser)

    if args.command == "config":
        return _config(args, parser)

    if args.command == "run":
        return _run(args, runs, parser)

    if args.command == "eval":
        return _eval(args, parser)

    if args.command in ("mcp", "skill"):
        return _inventory(args, inventory, parser)

    if args.command == "observe":
        return _observe(args, observer)

    if args.command == "propose":
        return _propose(args)

    if args.command == "resume":
        return _resume(args, resumer)

    findings = diagnose(probes())
    print(json.dumps(as_json(findings)) if args.json else _report(findings))
    return exit_code(findings)


def _propose(args: Any) -> int:
    """Say whether a configuration change may go to a reviewer."""
    from agent.src.improvement.propose import may_propose

    try:
        before = json.loads(pathlib.Path(args.before).read_text())
        after = json.loads(pathlib.Path(args.after).read_text())
    except OSError as missing:
        return _complain(str(missing), as_json=args.json)
    except json.JSONDecodeError as unreadable:
        return _complain(
            f"{args.before} or {args.after}: {unreadable}", as_json=args.json
        )

    found = may_propose(before=before, after=after)

    from agent.src.improvement.record import record_proposal

    record_proposal(
        before=before,
        after=after,
        permitted=found.permitted,
        reason=found.reason,
        source="cli",
    )

    if found.permitted:
        print(json.dumps({"permitted": True}) if args.json else "May be proposed.")
        return 0

    print(
        json.dumps({"permitted": False, "reason": found.reason})
        if args.json
        else f"Refused: {found.reason}"
    )
    return 1


def _complain(message: str, *, as_json: bool) -> int:
    """Say what went wrong, where a script will not eat it."""
    print(
        json.dumps({"ok": False, "error": message}) if as_json else message,
        file=sys.stderr,
    )
    return 1


def _ask(args: Any, asker: Callable[..., Any]) -> int:
    """One question, and an exit code a pipeline can branch on."""
    try:
        answer = asker(args.question, follow=getattr(args, "follow", False))
    except AskFailed as failed:
        return _complain(str(failed), as_json=args.json)

    return _say_answer(args, answer)


def _answer_the_pause(args: Any, waiting: dict) -> int | None:
    """Decide and resume, when there is somebody or an instruction."""
    from agent.cli.approve import decide
    from agent.cli.resume import ResumeFailed, resume_run

    found = decide(waiting, approve_all=getattr(args, "approve_all", False))
    if found is None:
        return None

    try:
        answer = resume_run(
            waiting["resume"]["thread_id"],
            found.decision,
            transport=_transport(),
            message=found.message,
        )
    except ResumeFailed as failed:
        return _complain(str(failed), as_json=args.json)

    return _say_answer(args, answer)


def _eval(args: Any, parser: argparse.ArgumentParser) -> int:
    """The checks, their usage, and one score (E28-T8)."""
    from agent.cli.evals import (
        EvalFailed,
        NotScorable,
        checks,
        score,
        usage,
        why_unused,
    )

    if args.action is None:
        parser.print_help(sys.stdout)
        return USAGE_ERROR

    transport = _transport()
    try:
        if args.action == "list":
            found = checks(transport=transport)
            if args.json:
                print(json.dumps({"checks": [vars(one) for one in found]}))
            elif not found:
                print("This deployment declares no checks.")
            else:
                for one in found:
                    how = (
                        f"judged by {one.judge}"
                        if one.kind == "judged"
                        else f"{one.kind} over {one.corpus or 'an unnamed corpus'}"
                    )
                    print(f"{one.group:20} {one.name}  ({how})")
                    if one.decides:
                        print(f"{'':20} {one.decides}")
            return 0

        if args.action == "usage":
            report = usage(transport=transport)
            if args.json:
                print(
                    json.dumps(
                        {
                            "rows": [{"name": n, "runs": c} for n, c in report.rows],
                            "unused": report.unused,
                            "note": why_unused(report),
                        }
                    )
                )
                return 0
            for name, count in report.rows:
                print(f"{count:5}  {name}")
            if report.unused:
                print(f"\nNever run: {', '.join(report.unused)}")
                print(why_unused(report))
            return 0

        if args.action == "run":
            try:
                scored = score(args.check, transport=transport)
            except NotScorable as nothing:
                return _complain(f"Not scored: {nothing}", as_json=args.json)
            if args.json:
                print(json.dumps(scored))
            else:
                print(json.dumps(scored, indent=2))
            return 0
    except EvalFailed as failed:
        return _complain(str(failed), as_json=args.json)

    parser.print_help(sys.stdout)
    return USAGE_ERROR


def _say_answer(args: Any, answer: Any) -> int:
    """How an answer — or another pause — is reported."""
    waiting = getattr(answer, "paused", None)
    if waiting is not None:
        answered = _answer_the_pause(args, waiting)
        if answered is not None:
            return answered
        if args.json:
            print(json.dumps(waiting), file=sys.stderr)
        else:
            actions = ", ".join(a["action"] for a in waiting["awaiting"])
            print(
                f"Waiting for a decision on: {actions}. "
                f"Continue conversation {waiting['resume']['thread_id']} to "
                f"{_either(waiting['resume']['decisions'])}.",
                file=sys.stderr,
            )
        return NEEDS_DECISION

    said = getattr(answer, "streamed_text", None) or answer.text
    if args.json:
        print(json.dumps({"ok": True, "answer": said, "thread_id": answer.thread_id}))
    elif answer.text:
        print(answer.text)
    return 0


def _thread(args: Any, ops: Any, parser: argparse.ArgumentParser) -> int:
    """Conversations. Every refusal is a failure, never an empty answer."""
    if args.action is None:
        parser.print_help(sys.stdout)
        return USAGE_ERROR

    try:
        if args.action == "list":
            rows = ops.list_threads(transport=_transport())
            if args.json:
                print(
                    json.dumps(
                        {
                            "threads": [
                                {
                                    "thread_id": r.thread_id,
                                    "title": r.title,
                                    "status": r.status,
                                }
                                for r in rows
                            ]
                        }
                    )
                )
            elif not rows:
                print("No conversations.")
            else:
                for row in rows:
                    print(f"{row.thread_id}  {row.status or '-':8}  {row.title}")
            return 0

        if args.action == "show":
            print(json.dumps(ops.show_thread(args.thread_id, transport=_transport())))
            return 0

        if args.action == "rm":
            ops.remove_thread(args.thread_id, transport=_transport())
            if args.json:
                print(json.dumps({"ok": True, "removed": args.thread_id}))
            return 0

        if args.action == "fork":
            made = ops.fork_thread(args.thread_id, transport=_transport())
            print(json.dumps({"ok": True, "thread_id": made}) if args.json else made)
            return 0

    except ThreadFailed as failed:
        return _complain(str(failed), as_json=args.json)

    parser.print_help(sys.stdout)
    return USAGE_ERROR


def _run(args: Any, ops: Any, parser: argparse.ArgumentParser) -> int:
    """Runs. The operator's half."""
    if args.action is None:
        parser.print_help(sys.stdout)
        return USAGE_ERROR

    try:
        if args.action == "attach":
            from agent.cli.attach import AttachFailed, attach

            try:
                answer = attach(
                    args.thread_id,
                    args.run_id,
                    transport=_transport(),
                    follow=args.follow,
                )
            except AttachFailed as missing:
                return _complain(str(missing), as_json=args.json)
            return _say_answer(args, answer)

        if args.action == "list":
            rows = ops.list_runs(args.thread_id, transport=_transport())
            if args.json:
                print(
                    json.dumps(
                        {
                            "runs": [
                                {
                                    "run_id": r.run_id,
                                    "status": r.status,
                                    "error": r.error,
                                    "created_at": r.created_at,
                                }
                                for r in rows
                            ],
                            "unfinished": [r.run_id for r in ops.unfinished(rows)],
                        }
                    )
                )
            elif not rows:
                print("No runs.")
            else:
                for row in rows:
                    reason = f"  {row.error}" if row.error else ""
                    print(f"{row.run_id}  {row.status:10}  {row.created_at}{reason}")
            return 0

        if args.action == "show":
            print(
                json.dumps(
                    ops.show_run(args.thread_id, args.run_id, transport=_transport())
                )
            )
            return 0

        if args.action == "cancel":
            ops.cancel_run(args.thread_id, args.run_id, transport=_transport())
            if args.json:
                print(json.dumps({"ok": True, "cancelled": args.run_id}))
            return 0

    except RunFailed as failed:
        return _complain(str(failed), as_json=args.json)

    parser.print_help(sys.stdout)
    return USAGE_ERROR


def _integration(args: Any, ops: Any) -> int:
    """Connect, check or drop one integration."""
    import time

    transport = _transport()

    if args.action == "status":
        connected, account = ops.connection_status(args.name, transport=transport)
        if args.json:
            print(
                json.dumps(
                    {"name": args.name, "connected": connected, "account": account}
                )
            )
        else:
            print(
                f"{args.name}: {'connected' if connected else 'not connected'}"
                + (f" as {account}" if account else "")
            )
        return 0 if connected else DEGRADED_EXIT

    if args.action == "disconnect":
        ops.disconnect(args.name, transport=transport)
        print(
            f"{args.name}: token forgotten. `harness mcp connect {args.name}` to sign in again."
        )
        return 0

    started = ops.begin_connect(args.name, transport=transport)
    if args.json:
        print(json.dumps({"name": args.name, "authorize_url": started.authorize_url}))
    else:
        print(f"Open this to connect {args.name}:\n\n  {started.authorize_url}\n")
        print("This replaces any authorize URL already issued for this server.")

    if args.open:
        import webbrowser

        webbrowser.open(started.authorize_url)

    if not args.wait:
        return 0

    deadline = time.time() + args.wait
    while time.time() < deadline:
        connected, account = ops.connection_status(args.name, transport=transport)
        if connected:
            print(f"{args.name}: connected{f' as {account}' if account else ''}.")
            return 0
        time.sleep(2)
    print(f"{args.name}: still not connected after {args.wait}s.")
    return DEGRADED_EXIT


def _inventory(args: Any, ops: Any, parser: argparse.ArgumentParser) -> int:
    """What the agent is connected to, and what it knows."""
    if args.action is None:
        parser.print_help(sys.stdout)
        return USAGE_ERROR

    try:
        if args.command == "mcp" and args.action in ("connect", "status", "disconnect"):
            return _integration(args, ops)
        if args.command == "mcp":
            rows = ops.list_servers(transport=_transport())
            if args.json:
                print(
                    json.dumps(
                        {
                            "servers": [
                                {
                                    "name": r.name,
                                    "display_name": r.display_name,
                                    "enabled": r.enabled,
                                    "auth_mode": r.auth_mode,
                                    "connected": r.connected,
                                    "account": r.account,
                                }
                                for r in rows
                            ]
                        }
                    )
                )
            elif not rows:
                print("No integrations configured.")
            else:
                for row in rows:
                    state = (
                        "unknown"
                        if row.connected is None
                        else "connected"
                        if row.connected
                        else "not connected"
                    )
                    account = f"  {row.account}" if row.account else ""
                    print(f"{row.name:20} {state:14}{account}")
            return 0

        rows = ops.list_skills(transport=_transport())
        if args.json:
            print(
                json.dumps(
                    {
                        "skills": [
                            {"name": r.name, "description": r.description} for r in rows
                        ]
                    }
                )
            )
        elif not rows:
            print("No skills.")
        else:
            for row in rows:
                print(f"{row.name:24} {row.description}")
        return 0

    except InventoryFailed as failed:
        return _complain(str(failed), as_json=args.json)


def _observe(args: Any, ops: Any) -> int:
    """Observations from the agent's own runs. Never suggestions."""
    try:
        found = ops.collect(transport=_transport(), limit=args.limit, since=args.since)
    except ObserveFailed as failed:
        return _complain(str(failed), as_json=args.json)

    made: list[Any] = []
    if getattr(args, "propose", False):
        try:
            made = ops.proposals_for(
                found, transport=_transport(), max_per_run=args.max or None
            )
        except ObserveFailed as failed:
            _complain(str(failed), as_json=args.json)

    if args.json:
        print(
            json.dumps(
                {
                    "proposals": [
                        {
                            "kind": p.kind,
                            "detail": p.detail,
                            "argument": p.argument,
                            "seen": p.seen,
                            "runs": p.runs,
                            "path": p.path,
                            "diff": p.diff,
                            "permitted": p.permitted,
                            "refusal": p.refusal,
                            "blocked": p.blocked,
                            "probe": None
                            if p.probe is None
                            else {
                                "change": p.probe.change,
                                "touched": p.probe.touched,
                                "used": p.probe.used,
                                "runs": p.probe.runs,
                                "verdict": p.probe.verdict,
                                "rerun": p.probe.rerun,
                            },
                        }
                        for p in made
                    ],
                    "observations": [
                        {
                            "kind": o.kind,
                            "detail": o.detail,
                            "seen": o.seen,
                            "runs": o.runs,
                            "last_seen": o.last_seen,
                        }
                        for o in found.observations
                    ],
                    "read": found.read,
                    "unreadable": found.unreadable,
                }
            )
        )
        return 0

    for o in found.observations:
        when = f"  last seen {o.last_seen}" if o.last_seen else ""
        print(f"{o.seen:4}x  {o.kind:18} {o.detail}{when}")
    if not found.observations:
        print("Nothing worth looking at.")
    print(f"\nRead {found.read} conversation(s).")
    if found.unreadable:
        print(f"Could not read {found.unreadable} — they are not counted above.")

    for one in made:
        print(f"\n— {one.kind}: {one.detail}")
        if one.blocked:
            print(f"  No change proposed: {one.blocked}")
            continue
        print(f"  {one.argument}")
        if not one.permitted:
            print(f"  Refused: {one.refusal}")
            continue
        if one.probe is not None:
            print(f"  Against the runs behind it: {one.probe.verdict}")
        print(f"  {one.path}")
        print("".join(f"  {line}\n" for line in one.diff.splitlines()))
    if getattr(args, "propose", False) and not made:
        print("Nothing here implies a configuration change.")
    return 0


def _resume(args: Any, send: Any) -> int:
    """Answer a waiting run, and report whatever happens next."""
    try:
        answer = send(
            args.thread_id,
            args.decision,
            transport=_transport(),
            message=args.message,
        )
    except ResumeFailed as failed:
        return _complain(str(failed), as_json=args.json)

    return _say_answer(args, answer)


def _config(args: Any, parser: argparse.ArgumentParser) -> int:
    """The configuration tree. A refusal is never an empty answer."""
    from agent.cli.config import (
        ConfigFailed,
        ReadOnlyDeployment,
        SchemaMismatch,
        diff,
        list_files,
        render,
        set_file,
        show_file,
    )

    if args.action is None:
        parser.print_help(sys.stdout)
        return USAGE_ERROR

    transport = _transport()
    try:
        if args.action == "list":
            rows = list_files(transport=transport)
            if args.json:
                print(
                    json.dumps(
                        {
                            "files": [
                                {
                                    "path": r.path,
                                    "editable": r.editable,
                                    "bytes": r.bytes,
                                }
                                for r in rows
                            ]
                        }
                    )
                )
            else:
                for row in rows:
                    print(f"{'rw' if row.editable else 'r '}  {row.path}")
            return 0

        if args.action == "diff":
            found = diff(transport=transport)
            if args.json:
                print(json.dumps({"diff": found}))
            elif found:
                print(found, end="")
            else:
                print("Nothing has been edited away from the tree.")
            return 0

        if args.action == "render":
            made = render(transport=transport, out=args.out)
            if args.json:
                print(
                    json.dumps(
                        {
                            "written": made.written,
                            "skipped": made.skipped,
                            "out": args.out,
                        }
                    )
                )
            else:
                print(f"Wrote {len(made.written)} file(s) to {args.out}")
                if made.skipped:
                    print(
                        f"Skipped {len(made.skipped)}: this deployment serves "
                        "/config/file only for the editable set"
                    )
            return 0

        if args.action == "show":
            shown = show_file(args.path, transport=transport)
            if args.json:
                print(
                    json.dumps(
                        {
                            "path": shown.path,
                            "content": shown.content,
                            "version": shown.version,
                            "exists": shown.exists,
                        }
                    )
                )
            else:
                sys.stdout.write(shown.content)
            return 0

        text = (
            sys.stdin.read()
            if args.source == "-"
            else open(args.source, encoding="utf-8").read()
        )
        written = set_file(args.path, text, transport=transport, force=args.force)
        if args.json:
            print(json.dumps({"ok": True, **written}))
        else:
            lasting = (
                ""
                if written.get("durable")
                else " (not durable: this deployment "
                "keeps edits only while the process lives)"
            )
            print(
                f"{written.get('path')} is now version {written.get('version')}{lasting}"
            )
        return 0
    except ReadOnlyDeployment as refused:
        return _complain(str(refused), as_json=args.json)
    except SchemaMismatch as mismatch:
        return _complain(f"Schema mismatch: {mismatch}", as_json=args.json)
    except ConfigFailed as failed:
        return _complain(str(failed), as_json=args.json)
    except OSError as unreadable:
        return _complain(str(unreadable), as_json=args.json)


def _either(options: list[str]) -> str:
    """`a, b or c` rather than `a or b or c`."""
    if len(options) <= 1:
        return "".join(options)
    return f"{', '.join(options[:-1])} or {options[-1]}"


def _transport() -> Any:
    from agent.cli.transport import HttpTransport

    return HttpTransport(_base_url())


def main(*args: Any, **kwargs: Any) -> int:
    """`_dispatch`, with the one failure every command shares."""
    quieten_libraries()
    try:
        return _dispatch(*args, **kwargs)
    except Unauthenticated as expired:
        print(str(expired), file=sys.stderr)
        return UNAUTHENTICATED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
