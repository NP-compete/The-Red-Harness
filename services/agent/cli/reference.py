"""The command reference and the completions, generated (E28-T12)."""

from __future__ import annotations

import argparse
from typing import Any

SHELLS = ("bash", "zsh", "fish")


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, Any]:
    for action in parser._actions:  # noqa: SLF001 - argparse has no public API
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return dict(action.choices)
    return {}


def _options(parser: argparse.ArgumentParser) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            continue
        if isinstance(action, argparse._HelpAction):  # noqa: SLF001
            continue
        names = ", ".join(f"`{one}`" for one in action.option_strings)
        if not names:
            names = f"`{action.dest}`"
        found.append((names, (action.help or "").strip()))
    return found


def reference(parser: argparse.ArgumentParser) -> str:
    """The whole command surface, as a page."""
    lines = [
        "# `harness`",
        "",
        "Generated from the parser by `make cli-docs`. Edit the",
        "command, not this file — a page kept by hand is wrong the",
        "first time somebody adds a flag.",
        "",
        (parser.description or "").strip(),
        "",
    ]
    if parser.epilog:
        lines += ["```", parser.epilog.strip(), "```", ""]

    for name, sub in sorted(_subparsers(parser).items()):
        lines += [f"## `harness {name}`", ""]
        if sub.description or sub.format_usage():
            summary = (sub.description or "").strip()
            if summary:
                lines += [summary, ""]
        nested = _subparsers(sub)
        if nested:
            for child_name, child in sorted(nested.items()):
                lines += [f"### `harness {name} {child_name}`", ""]
                lines += _table(_options(child)) + [""]
            continue
        lines += _table(_options(sub)) + [""]
    return "\n".join(lines).rstrip() + "\n"


def _table(options: list[tuple[str, str]]) -> list[str]:
    rows = [(names, help_) for names, help_ in options if names != "`help`"]
    if not rows:
        return ["Takes no arguments."]
    return [
        "| | |",
        "|---|---|",
        *[f"| {names} | {help_} |" for names, help_ in rows],
    ]


def completion(shell: str, parser: argparse.ArgumentParser) -> str:
    """A completion script for one shell."""
    if shell not in SHELLS:
        raise ValueError(f"no completion for {shell!r}; try {', '.join(SHELLS)}")

    commands = sorted(_subparsers(parser))
    words = " ".join(commands)

    if shell == "bash":
        return (
            '# harness completion for bash — eval "$(harness completion bash)"\n'
            "_harness() {\n"
            f'  local commands="{words}"\n'
            '  COMPREPLY=($(compgen -W "$commands" -- "${COMP_WORDS[1]}"))\n'
            "}\n"
            "complete -F _harness harness\n"
        )
    if shell == "zsh":
        return (
            '# harness completion for zsh — eval "$(harness completion zsh)"\n'
            "_harness() {\n"
            f"  local -a commands=({words})\n"
            "  _describe 'command' commands\n"
            "}\n"
            "compdef _harness harness\n"
        )
    return (
        "# harness completion for fish — harness completion fish | source\n"
        + "".join(
            f"complete -c harness -n __fish_use_subcommand -a {name}\n"
            for name in commands
        )
    )
