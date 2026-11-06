#!/usr/bin/env python
"""Produce a clean `config/` from the shipped example."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "config" / "agent"

_CARRY_OVER = (
    "runtime/agent.yaml",
    "runtime/observability.yaml",
    "runtime/pii.yaml",
    "runtime/router.yaml",
    "runtime/ui.yaml",
    "runtime/secrets.example.yaml",
    "compliance/policies",
    "deployment/values.yaml",
)

_PROMPT = """---
name: orchestrator
description: >
  {description}
---

# {name}

You are {name}.

Replace this with the agent's actual instructions: what it is for, what
it must not do, and how it should behave when it is unsure.

## Guidelines

- State what the agent does and does not handle.
- Describe the tone and format of its answers.
- Name the subagents or skills it should prefer, if any.
"""

_MCP = """{
    "mcpServers": {}
}
"""


def _replace_agent_name(text: str, name: str) -> str:
    """Swap the example's identity for the new one."""
    return re.sub(
        r"^name:.*$",
        f'name: "{name}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )


def scaffold(name: str, out: Path, *, force: bool = False) -> list[str]:
    """Write a clean config tree. Returns what was created."""
    if out.exists() and any(out.iterdir()) and not force:
        raise FileExistsError(
            f"{out} already exists and is not empty — pass --force to overwrite"
        )

    created: list[str] = []
    out.mkdir(parents=True, exist_ok=True)

    for relative in _CARRY_OVER:
        source = EXAMPLE / relative
        target = out / relative
        if not source.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            text = source.read_text()
            if relative == "runtime/agent.yaml":
                text = _replace_agent_name(text, name)
            target.write_text(text)
        created.append(relative)

    (out / "PROMPT.md").write_text(
        _PROMPT.format(name=name, description=f"Main coordinator for {name}.")
    )
    created.append("PROMPT.md")

    mcp_path = out / "integrations" / "mcp.json"
    mcp_path.parent.mkdir(parents=True, exist_ok=True)
    mcp_path.write_text(_MCP)
    created.append("integrations/mcp.json")

    for empty in ("skills", "subagents"):
        (out / empty).mkdir(exist_ok=True)
        (out / empty / ".gitkeep").touch()
        created.append(f"{empty}/")

    return created


def main() -> int:
    """Scaffold a new agent from the template. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Display name of the agent")
    parser.add_argument(
        "--out",
        default=None,
        help="Where to write (default: ./config/agent-new)",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out = Path(args.out) if args.out else REPO / "config" / "agent-new"

    try:
        created = scaffold(args.name, out, force=args.force)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Created {out}:")
    for item in created:
        print(f"    {item}")
    print(
        "\nNext:\n"
        f"    1. Write {out}/PROMPT.md — it is a placeholder\n"
        "    2. Add MCP servers to mcp.json, skills to skills/\n"
        f"    3. CONFIG_PATH={out} make validate-config\n"
        "\nIt should report 0 errors and 0 warnings. The shipped example\n"
        "reports warnings by design; a real agent should not."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
