"""Frontmatter parsing and runtime value injection."""

from pathlib import Path
from typing import Any

import yaml


def parse_frontmatter(path: Path) -> dict[str, Any]:
    """Parse a markdown file with YAML frontmatter."""
    from agent.src.agent.config.resolution import effective_text

    content = effective_text(path)
    if not content.startswith("---"):
        return {"body": content.strip()}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {"body": content.strip()}

    frontmatter: dict[str, Any] = yaml.safe_load(parts[1]) or {}
    frontmatter["body"] = parts[2].strip()
    return frontmatter
