"""One command, one role (E10-T19)."""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    """The directory holding `pyproject.toml`, searched for.

    Duplicated from `agent._root` on purpose: CLI-1 keeps this
    tree off the package, and six lines is a cheaper price than
    the import. Counted hops would be wrong in the image, where
    `services/agent` is copied to `/app/agent`.
    """
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return here.parents[2]


REPO_ROOT = _repo_root()

# `services/ui` in a checkout; the image puts the built SPA at
# `/app/ui`, so fall back to whichever is actually there.
_UI_CANDIDATES = (REPO_ROOT / "services" / "ui", REPO_ROOT / "ui")
UI_DIR = os.environ.get("UI_DIR") or str(
    next((one for one in _UI_CANDIDATES if one.is_dir()), _UI_CANDIDATES[0])
)

ABSENT = {
    "acp": (
        "the ACP server is not in this image. `harness agent` serves the "
        "Agent Protocol routes; ACP is a separate surface and not built here."
    ),
}


class RoleFailed(RuntimeError):
    """This image cannot serve that role."""


def agent_command() -> list[str]:
    """The API server, exactly as the container has always started it."""
    return [sys.executable, "-m", "agent.aegra.entrypoint"]


def worker_command() -> list[str]:
    """The Temporal worker (E18-T3)."""
    return [sys.executable, "-m", "agent.src.workflows.entrypoint"]


POLICY_DIR = os.environ.get("OPA_POLICY_DIR") or str(
    Path(os.environ.get("CONFIG_PATH") or REPO_ROOT / "config" / "agent")
    / "compliance"
    / "policies"
)


def opa_enabled() -> bool:
    """Whether this deployment authorizes through OPA."""
    return os.environ.get("OPA_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def opa_command(*, policy_dir: str | None = None) -> list[str]:
    """The policy server, from the binary this image already carries."""
    where = Path(policy_dir or POLICY_DIR)
    if not where.is_dir():
        raise RoleFailed(
            f"{where} is not there, so there are no policies to serve. "
            "Set OPA_POLICY_DIR, or CONFIG_PATH to the config tree's root."
        )
    binary = shutil.which("opa")
    if not binary:
        raise RoleFailed("opa is not on PATH, so the opa role cannot start")
    return [
        binary,
        "run",
        "--server",
        f"--addr=:{os.environ.get('OPA_PORT', '8181')}",
        "--log-format=json",
        str(where),
    ]


def eval_worker_command() -> list[str]:
    """The eval worker.

    No Temporal. Its queue is the `evals` table, claimed with a
    lease — an eval is idempotent, so the guarantee durable
    execution sells is one it does not need, and requiring it
    would tie evals to `event_service_enabled`.
    """
    return [sys.executable, "-m", "agent.src.evals.worker"]


def ui_command(*, ui_dir: str | None = None) -> list[str]:
    """The BFF, serving the built SPA."""
    where = Path(ui_dir or UI_DIR)
    built = where / "dist" / "server" / "index.js"
    if not built.is_file():
        raise RoleFailed(
            f"{built} is not there. The ui role serves the built SPA; run "
            f"`npm run build` in {where}, or set UI_DIR if the checkout is "
            "somewhere else."
        )
    node = shutil.which("node")
    if not node:
        raise RoleFailed("node is not on PATH, so the ui role cannot start")
    return [node, str(built)]


def command_for(role: str, *, ui_dir: str | None = None) -> list[str]:
    """The argv one role becomes."""
    if role in ABSENT:
        raise RoleFailed(ABSENT[role])
    if role == "agent":
        return agent_command()
    if role == "ui":
        return ui_command(ui_dir=ui_dir)
    if role == "worker":
        return worker_command()
    if role == "opa":
        return opa_command()
    if role == "eval-worker":
        return eval_worker_command()
    raise RoleFailed(
        f"no role called {role!r}; try agent, ui, worker, eval-worker, opa or all"
    )


def serve(
    role: str,
    *,
    ui_dir: str | None = None,
    exec_: Callable[[str, Sequence[str]], object] | None = None,
    write: Callable[[str], object] | None = None,
) -> int:
    """Become the role, or say why not."""
    say = write or (lambda line: print(line, file=sys.stderr))
    run = exec_ or os.execv

    if role == "all":
        return supervise(ui_dir=ui_dir, write=say)

    try:
        argv = command_for(role, ui_dir=ui_dir)
    except RoleFailed as refused:
        say(f"Cannot serve {role!r}: {refused}")
        return 2

    if role == "ui":
        os.chdir(Path(ui_dir or UI_DIR))

    say(f"harness {role}: {' '.join(argv)}")
    run(argv[0], argv)
    return 1


UI_ENV_PREFIX = "UIENV_"


def child_env(role: str) -> dict[str, str]:
    """The environment one supervised child should see."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(UI_ENV_PREFIX)}
    if role != "ui":
        return env

    env = {k: v for k, v in env.items() if v != ""}

    for key, value in os.environ.items():
        if key.startswith(UI_ENV_PREFIX):
            env[key[len(UI_ENV_PREFIX) :]] = value
    return env


def _cwd_for(role: str, ui_dir: str | None) -> str | None:
    """The interface resolves its built client relative to cwd."""
    return str(Path(ui_dir or UI_DIR)) if role == "ui" else None


def supervise(
    *, ui_dir: str | None = None, write: Callable[[str], object] | None = None
) -> int:
    """Every role this deployment wants, in one process tree."""
    import signal
    import subprocess

    say = write or (lambda line: print(line, file=sys.stderr))
    say(
        "harness all: a supervisor, for Kind and demos. Production runs one "
        "role per container — a supervisor muddles signals and makes one "
        "liveness probe answer for two things."
    )

    children: list[Any] = []

    def stop(signum: int, _frame: object) -> None:
        for child in children:
            child.send_signal(signum)

    roles = ["agent", "ui"]
    if opa_enabled():
        roles.insert(0, "opa")

    for role in roles:
        try:
            argv = command_for(role, ui_dir=ui_dir)
        except RoleFailed as refused:
            say(f"Cannot serve {role!r}: {refused}")
            for child in children:
                child.terminate()
            return 2
        children.append(
            subprocess.Popen(argv, env=child_env(role), cwd=_cwd_for(role, ui_dir))
        )

    for received in (signal.SIGTERM, signal.SIGINT):
        signal.signal(received, stop)

    first = os.wait()[1] if children else 0
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=10)
        except Exception:  # noqa: BLE001 - a child that will not go
            child.kill()
    return os.waitstatus_to_exitcode(first) if first else 0
