"""Finding a setting that was written twice."""

from __future__ import annotations

import yaml


def _walk(node: yaml.Node, path: str, found: list[str]) -> None:
    if isinstance(node, yaml.MappingNode):
        seen: dict[str, int] = {}
        for key_node, value_node in node.value:
            name = getattr(key_node, "value", None)
            if not isinstance(name, str):
                continue
            here = f"{path}.{name}" if path else name
            if name in seen:
                found.append(
                    f"'{here}' is set more than once "
                    f"(line {key_node.start_mark.line + 1}, "
                    f"first at line {seen[name]}); "
                    "the last one wins and the others are discarded"
                )
            else:
                seen[name] = key_node.start_mark.line + 1
            _walk(value_node, here, found)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            _walk(item, path, found)


def duplicate_keys(text: str) -> list[str]:
    """Every key set more than once in the same mapping."""
    try:
        root = yaml.compose(text)
    except yaml.YAMLError:
        return []
    if root is None:
        return []

    found: list[str] = []
    _walk(root, "", found)
    return found
