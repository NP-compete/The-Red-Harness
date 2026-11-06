"""Profile fields an administrator may correct (E9-T2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

PROFILE_FIELDS: tuple[str, ...] = (
    "display_name",
    "title",
    "locale",
    "timezone",
    "contact",
)

MAX_FIELD_CHARS = 256

CREATE_PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id       TEXT PRIMARY KEY,
    display_name  TEXT,
    title         TEXT,
    locale        TEXT,
    timezone      TEXT,
    contact       TEXT,
    updated_by    TEXT NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


class ProfileError(ValueError):
    """A write that was refused before it reached the database."""


@dataclass(frozen=True)
class Profile:
    """One user's profile fields, and who last changed them."""

    user_id: str
    fields: dict[str, str]
    updated_by: str | None = None
    updated_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """The profile as a plain dictionary."""
        return {
            "user_id": self.user_id,
            "fields": dict(self.fields),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at,
        }


def validate(changes: dict[str, Any]) -> dict[str, str]:
    """The changes, or a refusal naming the field that is wrong."""
    if not changes:
        raise ProfileError("no fields given")

    unknown = sorted(set(changes) - set(PROFILE_FIELDS))
    if unknown:
        raise ProfileError(
            f"not profile fields: {', '.join(unknown)}. "
            f"This surface writes only {', '.join(PROFILE_FIELDS)}; "
            "membership and entitlement belong to the identity provider."
        )

    clean: dict[str, str] = {}
    for name, value in changes.items():
        if value is None:
            clean[name] = ""
            continue
        if not isinstance(value, str):
            raise ProfileError(f"'{name}' must be text")
        if len(value) > MAX_FIELD_CHARS:
            raise ProfileError(
                f"'{name}' is {len(value)} characters, over the "
                f"{MAX_FIELD_CHARS} allowed"
            )
        clean[name] = value
    return clean
