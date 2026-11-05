"""The library, as something the model can call."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.membership import teams_of_sync
from agent.src.knowledge.retrieval import RetrievalRefused, retrieve
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.security.fencing import fence
from agent.src.token_budget.identity import resolve_thread_id, resolve_user_id
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

NAME = "search_documents"


class _Arguments(BaseModel):
    question: str = Field(description="What to look for")
    scope: str = Field(
        default="",
        description=(
            "Where to look: session for files in this conversation, "
            "user for the person's own documents, agent for this "
            "agent's reference material. Leave empty to try the "
            "narrowest first."
        ),
    )


def _nearly(found: Any) -> str:
    """A note about what almost matched, with no text in it."""
    near = getattr(found, "below_threshold", ()) or ()
    if not near:
        return ""
    count = len(near)
    thing = "document" if count == 1 else "documents"
    return (
        f" {count} {thing} nearly matched but scored too low to return; "
        f"a more specific question may reach them."
    )


def _describe(found: Any) -> str:
    if not found.documents:
        looked = ", ".join(scope.value for scope in found.searched) or "nowhere"
        return f"Nothing found in: {looked}.{_nearly(found)}"

    lines = [f"Found in {found.scope.value} documents:"]
    for document in found.documents:
        body = fence(document.text, source=f"the document {document.id}")
        lines.append(f"- [{document.id}] {document.title or document.id}\n  {body}")
    near = _nearly(found)
    if near:
        lines.append(near.strip())
    return "\n".join(lines)


def _artifact(found: Any) -> list[dict]:
    """Structure for the citation layer, which writes onto the turn."""
    entries = [
        {
            "id": hit.document.id,
            "title": hit.document.title,
            "text": hit.document.text,
            "scope": hit.document.scope.value,
            "score": round(hit.score, 3),
            "used": True,
        }
        for hit in (getattr(found, "hits", ()) or ())
    ]

    entries.extend(
        {
            "id": hit.document.id,
            "title": hit.document.title,
            "text": "",
            "scope": hit.document.scope.value,
            "score": round(hit.score, 3),
            "used": False,
        }
        for hit in (getattr(found, "below_threshold", ()) or ())
    )
    return entries


def build_retrieval_tool(*, config: Knowledge, store: Any) -> Any:
    """A tool for searching the library, or nothing when there is none."""
    if not config.enabled:
        return None

    def _search(question: str, scope: str = "") -> tuple[str, list[dict]]:
        who = resolve_user_id() or ""
        viewer = Viewer(
            subject=who,
            teams=teams_of_sync(who),
            thread_id=resolve_thread_id(),
        )

        asked: Scope | None = None
        if scope:
            try:
                asked = Scope(scope)
            except ValueError:
                return (
                    f"{scope!r} is not somewhere this agent keeps documents. "
                    f"Try one of: {', '.join(s.value for s in config.scopes)}.",
                    [],
                )

        try:
            found = retrieve(
                question, store=store, viewer=viewer, config=config, scope=asked
            )
        except RetrievalRefused as refused:
            return str(refused), []
        except Exception as error:
            logger.warning("A document lookup failed: %s", error)
            return f"Could not search the documents just now: {error}", []

        return _describe(found), _artifact(found)

    return StructuredTool.from_function(
        func=_search,
        name=NAME,
        description=(
            "Search this agent's documents before answering from memory. "
            "Returns the matching documents with their identifiers, so an "
            "answer can say where it came from."
        ),
        args_schema=_Arguments,
        response_format="content_and_artifact",
    )
