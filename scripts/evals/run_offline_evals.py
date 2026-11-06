"""Run the checks a build can run, and fail only on what matters (E22-T2)."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

_SERVICES = str(REPO_ROOT / "services")
if _SERVICES not in sys.path:
    sys.path.insert(0, _SERVICES)

from agent.src.agent.config.paths import config_root  # noqa: E402
from agent.src.evals.offline import run_offline  # noqa: E402


def main() -> int:
    """Run the offline retrieval evals against an in-memory corpus."""
    from agent.src.agent.config import agent_config
    from agent.src.knowledge.ingest import sync_corpus
    from agent.src.knowledge.retrieval import retrieve
    from agent.src.knowledge.scopes import Scope, Viewer
    from agent.src.knowledge.store import InMemoryStore

    root = config_root()
    config = agent_config.get_knowledge_config()

    store = InMemoryStore()
    corpus = root / "knowledge"
    if corpus.is_dir():
        sync_corpus(
            root=corpus,
            store=store,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

    def _search_for(name: str) -> Callable[[str, int], list[str]]:
        """A search function bound to one scope."""
        scope = Scope(name)
        viewer = Viewer(subject="ci", teams=(), thread_id=None)

        def _search(query: str, k: int) -> list[str]:
            """Retrieve the top `k` document ids for `query`."""
            found = retrieve(
                query,
                store=store,
                viewer=viewer,
                config=_enabled(config),
                scope=scope,
            )
            return [hit.document.id for hit in list(found.hits)[:k]]

        return _search

    def _documents_for(name: str) -> list[str]:
        """Every document id in the named scope."""
        return [d.id for d in store.documents_in(scope=Scope(name))]

    report = run_offline(
        root,
        search_for=_search_for,
        config=config,
        document_ids_for=_documents_for,
    )
    print(report.say())
    return 0 if report.ok else 1


def _enabled(config: Any) -> Any:
    """The same settings with the library on."""
    import dataclasses

    return dataclasses.replace(config, enabled=True, scopes=_scopes(config))


def _scopes(config: Any) -> tuple[Any, ...]:
    """The scopes to evaluate, or all of them if none are configured."""
    from agent.src.knowledge.scopes import Scope

    return config.scopes or (Scope.SESSION, Scope.USER, Scope.TEAM, Scope.AGENT)


if __name__ == "__main__":
    sys.exit(main())
