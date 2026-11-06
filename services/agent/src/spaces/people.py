"""Who else is in this room, for `@` to offer (E41-T3)."""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

MAX_PEOPLE = 50


def members_of_group_sync(group_cn: str) -> tuple[str, ...]:
    """The handles the directory lists in this group, or nothing."""
    if not group_cn:
        return ()

    try:
        from ldap3 import SUBTREE

        from agent.src.ldap.service import (
            _ensure_bound,
            _escape_ldap_filter,
            _ldap_lock,
        )
    except Exception as error:  # pragma: no cover - import guard
        logger.warning("space_people_unavailable", error=str(error))
        return ()

    from agent.src.ldap.config import ldap_settings

    with _ldap_lock:
        conn = _ensure_bound()
        if conn is None:
            return ()
        try:
            ok = conn.search(
                ldap_settings.get_group_search_base(),
                f"(cn={_escape_ldap_filter(group_cn)})",
                search_scope=SUBTREE,
                attributes=["member", "uniqueMember", "memberUid"],
            )
            if not ok:
                return ()
            found: list[str] = []
            for entry in conn.entries:
                for attr in ("member", "uniqueMember", "memberUid"):
                    values = getattr(entry, attr, None)
                    if values is None:
                        continue
                    raw = values.values if hasattr(values, "values") else values
                    if not isinstance(raw, (list, tuple)):
                        raw = [raw]
                    for one in raw:
                        handle = _handle_of(str(one))
                        if handle and handle not in found:
                            found.append(handle)
            return tuple(found[:MAX_PEOPLE])
        except Exception as error:
            logger.warning(
                "space_people_unavailable", group_cn=group_cn, error=str(error)
            )
            return ()


def _handle_of(member: str) -> str:
    """`uid=ada,ou=users,dc=example` and `ada` are the same person."""
    value = member.strip()
    if not value:
        return ""
    if "=" not in value:
        return value
    first = value.split(",", 1)[0]
    return first.split("=", 1)[1].strip() if "=" in first else ""
