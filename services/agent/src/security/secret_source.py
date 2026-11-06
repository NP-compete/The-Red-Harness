"""Reading a secret by reference, from wherever it is kept."""

from __future__ import annotations

import os
from collections.abc import Callable

from agent.src.audit.emitter import emit_audit_event
from agent.src.audit.events import AuditEventType
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def _record(reference: str, source: str, *, found: bool) -> None:
    """Note that a secret was asked for, by reference."""
    try:
        emit_audit_event(
            AuditEventType.SECRET_RESOLVED,
            reference=reference,
            source=source,
            found=found,
        )
    except Exception:
        logger.debug("Could not record a secret resolution", exc_info=True)


class SecretUnavailable(RuntimeError):
    """A secret was asked for by reference and is not there."""


def from_environment(name: str) -> str | None:
    """The value of an environment variable, or nothing."""
    found = os.environ.get(name, "")
    return found if found.strip() else None


def _from_vault(reference: str) -> str | None:
    """The vault source, imported where it is used."""
    from agent.src.security.vault_source import from_vault

    return from_vault(reference)


SOURCES: dict[str, Callable[[str], str | None]] = {
    "env": from_environment,
    "vault": _from_vault,
}

KNOWN_BUT_UNBUILT = ("kms", "k8s")


def from_variable(name: str) -> str | None:
    """Read a variable, and follow it if it points somewhere."""
    held = os.environ.get(name, "").strip()
    if not held:
        return None
    if ":" not in held:
        return held
    return resolve(held)


def resolve(reference: str) -> str:
    """The secret this reference names."""
    asked = (reference or "").strip()
    if not asked:
        raise SecretUnavailable("a secret has to be asked for by name")

    source, _, name = asked.partition(":")
    if not name:
        source, name = "env", source

    if source in KNOWN_BUT_UNBUILT:
        raise SecretUnavailable(
            f"{asked} names the {source} source, which is not built yet. "
            "Point it at an environment variable instead."
        )

    read = SOURCES.get(source)
    if read is None:
        raise SecretUnavailable(
            f"{asked} names a source this does not know: {source!r}"
        )

    try:
        value = read(name)
    except Exception:
        _record(asked, source, found=False)
        raise
    else:
        _record(asked, source, found=value is not None)

    if value is None:
        raise SecretUnavailable(f"{name} is not set, so {asked} cannot be read")
    return value
