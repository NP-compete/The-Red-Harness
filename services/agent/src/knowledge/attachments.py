"""A file attached to a conversation is a session document."""

from __future__ import annotations

from typing import Any

from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.scopes import Scope
from agent.src.knowledge.store import Document
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

PREFIX = "attached:"


def remember_attachment(
    *,
    thread_id: str,
    filename: str,
    path: str,
    text: str,
    store: Any,
    config: Knowledge,
) -> bool:
    """Make an attachment's text searchable. Never raises."""
    if not config.enabled or Scope.SESSION not in config.scopes:
        return False

    if not thread_id or not text.strip():
        return False

    try:
        store.add(
            Document(
                id=f"{PREFIX}{thread_id}:{path}",
                text=text,
                scope=Scope.SESSION,
                thread_id=thread_id,
                title=filename,
                metadata={"path": path},
            )
        )
        return True
    except Exception as error:
        logger.warning("Could not make %s searchable: %s", filename, error)
        return False
