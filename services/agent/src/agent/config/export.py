"""The whole configuration as it now stands, ready to commit."""

from __future__ import annotations

_TREE = "config/agent"


def effective_tree() -> dict[str, str]:
    """Every configuration file, with any edit applied."""
    from agent.src.agent.config import resolution
    from agent.src.agent.config.paths import config_root

    root = config_root()
    out: dict[str, str] = {}

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        key = f"{_TREE}/{path.relative_to(root).as_posix()}"
        try:
            out[key] = resolution.effective_text(path)
        except (OSError, UnicodeDecodeError):
            continue

    overlay = resolution._overlay
    if overlay is not None:
        for key in overlay.overridden():
            if key.startswith(f"{_TREE}/") and key not in out:
                content = overlay.current(key)
                if content is not None:
                    out[key] = content

    return out
