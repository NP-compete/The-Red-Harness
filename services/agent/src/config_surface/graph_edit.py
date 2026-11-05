"""Changing the configuration from the diagram (E34-T3)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

EDITABLE_FIELDS: dict[str, tuple[str, ...]] = {
    "subagent": ("model",),
    "mcp": ("enabled",),
}


def _text(path: Path) -> str:
    """The file as the agent currently reads it, edits included."""
    from agent.src.agent.config.resolution import effective_text

    return effective_text(path)


class GraphEditRefused(ValueError):
    """A change the diagram cannot make, with the reason."""


def _refuse(what: str) -> None:
    raise GraphEditRefused(what)


def _front_matter_bounds(text: str) -> tuple[int, int]:
    """Where the `---` block starts and ends, by line number."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        _refuse("this file has no front matter to change")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return 1, index
    _refuse("the front matter in this file is not closed")
    raise AssertionError("unreachable")


def _set_scalar(text: str, key: str, value: str) -> str:
    """Rewrite `key: …` inside the front matter, leaving the rest alone."""
    start, end = _front_matter_bounds(text)
    lines = text.splitlines(keepends=True)
    pattern = re.compile(rf"^(\s*){re.escape(key)}\s*:\s*(.*)$")
    for index in range(start, end):
        match = pattern.match(lines[index].rstrip("\n"))
        if not match:
            continue
        if match.group(2).strip() in {"", ">", "|"}:
            _refuse(f"'{key}' is a block in this file and is not editable here")
        lines[index] = f"{match.group(1)}{key}: {value}\n"
        return "".join(lines)
    lines.insert(end, f"{key}: {value}\n")
    return "".join(lines)


def _server_span(text: str, server: str) -> tuple[int, int]:
    """Where this server's object starts and ends, by brace counting."""
    key = re.search(rf'"{re.escape(server)}"\s*:\s*\{{', text)
    if key is None:
        _refuse(f"no server named '{server}' in integrations/mcp.json")
        raise AssertionError("unreachable")

    depth, index = 0, key.end() - 1
    while index < len(text):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return key.end(), index
        index += 1
    _refuse(f"the entry for '{server}' in integrations/mcp.json is not closed")
    raise AssertionError("unreachable")


def _set_mcp_enabled(text: str, server: str, enabled: bool) -> str:
    """Flip `disabled` for one server in `mcp.json`, in place."""
    opens, closes = _server_span(text, server)
    body = text[opens:closes]

    existing = re.search(r'"disabled"\s*:\s*(true|false)', body)
    if existing is not None:
        said = "false" if enabled else "true"
        body = body[: existing.start()] + f'"disabled": {said}' + body[existing.end() :]
    elif enabled:
        return text
    else:
        separator = "" if not body.strip() else ", "
        body = f'"disabled": true{separator}{body.lstrip()}'
        leading = re.match(r"\s*", text[opens:])
        body = (leading.group(0) if leading else "") + body

    return text[:opens] + body + text[closes:]


def propose(*, node_id: str, field: str, value: Any, root: Path) -> tuple[str, str]:
    """The file this change lands in, and what it would then say."""
    kind, _, name = node_id.partition(":")
    if not name:
        _refuse(f"{node_id!r} does not name a node")

    allowed = EDITABLE_FIELDS.get(kind)
    if allowed is None:
        _refuse(
            f"a {kind} is drawn from the tree and is not editable from the "
            "diagram; open its file to change it"
        )
    if field not in (allowed or ()):
        _refuse(
            f"'{field}' is not editable on a {kind} from the diagram "
            f"({', '.join(allowed or ()) or 'nothing is'}). Open the file "
            "instead — a list or a block rewritten from here would lose the "
            "comments around it."
        )

    if kind == "subagent":
        path = root / "subagents" / f"{name}.md"
        if not path.is_file():
            _refuse(f"no subagent file for '{name}'")
        if not isinstance(value, str) or not value.strip():
            _refuse("a model is a name, and an empty one is not a change")
        return (
            f"config/agent/subagents/{name}.md",
            _set_scalar(_text(path), "model", value.strip()),
        )

    path = root / "integrations" / "mcp.json"
    if not path.is_file():
        _refuse("this tree has no integrations/mcp.json")
    if not isinstance(value, bool):
        _refuse("'enabled' is true or false")
    return (
        "config/agent/integrations/mcp.json",
        _set_mcp_enabled(_text(path), name, value),
    )
