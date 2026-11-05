"""The configuration that is not in the config tree (E25)."""

from __future__ import annotations

import os
import re
from typing import Any

SECRET_SEGMENTS = frozenset(
    {
        "SECRET",
        "SECRETS",
        "PASSWORD",
        "PASSWD",
        "TOKEN",
        "CREDENTIAL",
        "CREDENTIALS",
        "PRIVATE",
        "SALT",
        "DSN",
        "KEY",
        "KEYFILE",
        "APIKEY",
    }
)

MASK = "••••••"

_URL_WITH_CREDENTIALS = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://[^/\s:@]+:[^/\s@]+@")


def is_secret(name: str) -> bool:
    """True when any segment of the name is a secret word."""
    return any(part in SECRET_SEGMENTS for part in name.upper().split("_"))


def value_is_secret(value: Any) -> bool:
    """Whether `value` is a URL with credentials in it."""
    return isinstance(value, str) and bool(_URL_WITH_CREDENTIALS.match(value))


def _render(value: Any) -> Any:
    """`value` as something JSON can carry."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple, set)):
        return [_render(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _render(v) for k, v in value.items()}
    return str(value)


def _loosened(rows: list[dict[str, Any]]) -> list[str]:
    """The overridden settings whose change raised a limit."""
    from agent.src.agent.config_diff import diff_config

    before = {
        r["name"]: str(r["default"])
        for r in rows
        if r["overridden"] and not r["masked"]
    }
    after = {
        r["name"]: str(r["value"]) for r in rows if r["overridden"] and not r["masked"]
    }
    if not before and not after:
        return []
    return sorted(e.key for e in diff_config(before, after).changes if e.loosens)


def settings_view(settings: Any | None = None) -> dict[str, Any]:
    """Every settings field, with where its value came from."""
    if settings is None:
        from agent.src.settings import settings as live

        settings = live

    rows: list[dict[str, Any]] = []
    masked = 0
    for name, field in type(settings).model_fields.items():
        value = getattr(settings, name, None)
        default = field.default
        numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
        secret = (not numeric) and (is_secret(name) or value_is_secret(value))
        if secret:
            masked += 1
        from_env = name in os.environ
        rows.append(
            {
                "name": name,
                "value": MASK if secret else _render(value),
                "default": MASK if secret else _render(default),
                "from_env": from_env,
                "overridden": from_env and _render(value) != _render(default),
                "masked": secret,
                "description": (field.description or "")[:200],
            }
        )

    rows.sort(key=lambda r: (not r["overridden"], r["name"]))

    loosened = _loosened(rows)

    return {
        "fields": rows,
        "total": len(rows),
        "from_env": sum(1 for r in rows if r["from_env"]),
        "overridden": sum(1 for r in rows if r["overridden"]),
        "masked": masked,
        "loosened": loosened,
        "editable": False,
        "why_readonly": (
            "Settings are read from the process environment at startup. "
            "Change them where the process is started — the deployment "
            "manifest, the compose file, or .env — then restart."
        ),
    }
