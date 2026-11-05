"""Putting the citations on the answer."""

from __future__ import annotations

from typing import Any

from agent.src.knowledge.citing import cite
from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.scopes import Scope
from agent.src.knowledge.store import Document
from agent.src.knowledge.tools import NAME as SEARCH_TOOL
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def _entries_from(messages: Any) -> list[dict]:
    """Every row the lookups in this turn produced."""
    rows: list[dict] = []
    for message in messages or []:
        if getattr(message, "type", None) != "tool":
            continue
        if getattr(message, "name", "") != SEARCH_TOOL:
            continue
        artifact = getattr(message, "artifact", None)
        if isinstance(artifact, list):
            rows.extend(entry for entry in artifact if isinstance(entry, dict))
    return rows


def _looked_at(entries: list[dict]) -> list[dict]:
    """What the search weighed, and how each scored."""
    best: dict[str, dict] = {}
    for entry in entries:
        key = str(entry.get("id") or "")
        score = entry.get("score")
        if not key or score is None:
            continue

        row = best.get(key)
        if row is None:
            best[key] = {
                "id": key,
                "title": str(entry.get("title") or ""),
                "scope": str(entry.get("scope") or ""),
                "score": score,
                "used": bool(entry.get("used", True)),
            }
            continue

        if score > row["score"]:
            row["score"] = score
            row["title"] = str(entry.get("title") or "") or row["title"]
        row["used"] = row["used"] or bool(entry.get("used", True))

    return list(best.values())


def _documents_from(messages: Any) -> list[Document]:
    """Everything the lookups in this turn returned."""
    found: list[Document] = []
    for message in messages or []:
        if getattr(message, "type", None) != "tool":
            continue
        if getattr(message, "name", "") != SEARCH_TOOL:
            continue

        artifact = getattr(message, "artifact", None)
        if not isinstance(artifact, list):
            continue

        for entry in artifact:
            if not isinstance(entry, dict):
                continue
            try:
                found.append(
                    Document(
                        id=str(entry["id"]),
                        text=str(entry.get("text") or ""),
                        scope=Scope(entry.get("scope") or "agent"),
                        title=str(entry.get("title") or ""),
                    )
                )
            except (KeyError, ValueError):
                continue
    return found


def _notes(extra: dict) -> dict:
    """The turn's notes, made if absent."""
    notes = extra.get("answer_notes")
    if not isinstance(notes, dict):
        notes = {}
        extra["answer_notes"] = notes
    return notes


def stamp_citations(message: Any, messages: Any) -> None:
    """Write onto the answer which documents it came from."""
    try:
        extra = getattr(message, "additional_kwargs", None)
        if extra is None:
            return

        entries = _entries_from(messages)
        looked = _looked_at(entries)
        if looked:
            _notes(extra)["retrieval"] = looked

        from agent.src.security.untrusted_reads import sources_behind

        outside = sources_behind(str(getattr(message, "content", "") or ""))
        if outside:
            _notes(extra)["from_outside"] = list(outside)

        documents = _documents_from(messages)
        if not documents:
            return

        from agent.src.knowledge.retrieval import Found

        cited = cite(
            answer=str(getattr(message, "content", "") or ""),
            found=Found(documents=documents),
        )
        if not cited:
            return

        _notes(extra)["citations"] = [citation.as_dict() for citation in cited]
    except Exception:
        logger.debug("Could not record citations", exc_info=True)


def build_citation_middleware(*, config: Knowledge) -> Any:
    """Record where an answer came from, when there is a library."""
    if not config.enabled:
        return None

    from langchain.agents.middleware import AgentMiddleware

    class CitationMiddleware(AgentMiddleware):
        """Name the documents an answer borrowed from."""

        async def awrap_model_call(self, request: Any, handler: Any) -> Any:
            return self._note(request, await handler(request))

        def wrap_model_call(self, request: Any, handler: Any) -> Any:
            return self._note(request, handler(request))

        @staticmethod
        def _note(request: Any, response: Any) -> Any:
            message: Any = getattr(response, "result", None)
            if isinstance(message, list):
                message = message[0] if message else None
            if message is not None:
                stamp_citations(message, getattr(request, "messages", None))
            return response

    return CitationMiddleware()
