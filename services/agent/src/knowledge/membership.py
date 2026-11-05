"""Which teams a reader is in, asked of the directory (E31-T1)."""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


def configured_teams() -> tuple[str, ...]:
    """The groups this deployment has a team corpus for."""
    try:
        from agent.src.agent.config import agent_config

        return tuple(agent_config.get_knowledge_config().teams)
    except Exception as error:
        logger.warning("knowledge_teams_unreadable", error=str(error))
        return ()


def _teams_with_documents() -> tuple[str, ...]:
    """Groups that actually have a corpus in the store."""
    try:
        from agent.src.knowledge.scopes import Scope
        from agent.src.knowledge.store import session_store

        return tuple(
            sorted(
                {
                    document.team
                    for document in session_store().documents_in(scope=Scope.TEAM)
                    if document.team
                }
            )
        )
    except Exception as error:
        logger.warning("knowledge_team_documents_unreadable", error=str(error))
        return ()


def candidate_teams() -> tuple[str, ...]:
    """Every group worth asking the directory about."""
    found = list(configured_teams())
    found.extend(team for team in _teams_with_documents() if team not in found)
    return tuple(found)


def _shortcut(user_id: str) -> tuple[str, ...] | None:
    """The answer when there is no question to ask, or None."""
    if not candidate_teams():
        return ()
    if not user_id:
        return ()
    return None


def teams_of_sync(user_id: str) -> tuple[str, ...]:
    """The same answer, for the retrieval tool, which is not async."""
    shortcut = _shortcut(user_id)
    if shortcut is not None:
        return shortcut

    from agent.src.ldap.service import _is_user_in_group_sync

    found: list[str] = []
    for group in candidate_teams():
        try:
            if _is_user_in_group_sync(user_id, group):
                found.append(group)
        except Exception as error:
            logger.warning("knowledge_team_unavailable", group=group, error=str(error))
    return tuple(found)


async def teams_of(user_id: str) -> tuple[str, ...]:
    """The configured teams this person is actually in."""
    shortcut = _shortcut(user_id)
    if shortcut is not None:
        return shortcut

    try:
        from agent.src.ldap import resolve_user_groups

        return tuple(await resolve_user_groups(user_id, candidate_teams()))
    except Exception as error:
        logger.warning("knowledge_teams_unavailable", user_id=user_id, error=str(error))
        return ()
