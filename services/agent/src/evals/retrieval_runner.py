"""Running a declared retrieval check, and keeping the score (E22-T3)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from agent.src.evals.retrieval_quality import Measurement, measure, read_cases

RESULTS_FILE = "evals/results.jsonl"


def results_store() -> Any:
    """The store results are appended to."""
    from agent.src.data_paths import data_dir
    from agent.src.evals.results import ResultsStore

    return ResultsStore(data_dir() / RESULTS_FILE)


def retrieval_fingerprint(config: Any, document_ids: Sequence[str]) -> str:
    """What this score is a score *of*."""
    said = json.dumps(
        {
            "chunk_size": getattr(config, "chunk_size", None),
            "chunk_overlap": getattr(config, "chunk_overlap", None),
            "top_k": getattr(config, "top_k", None),
            "min_score": getattr(config, "min_score", None),
            "documents": sorted(document_ids),
        },
        sort_keys=True,
    )
    return hashlib.sha256(said.encode()).hexdigest()[:12]


def cases_for(check: Any, root: Path) -> list[Any]:
    """The cases a declared check points at."""
    if not getattr(check, "dataset", ""):
        raise ValueError(
            f"the check '{check.name}' names no dataset, so there is nothing "
            "to retrieve for"
        )
    path = root / check.dataset
    if not path.is_file():
        raise ValueError(f"the dataset '{check.dataset}' does not exist")

    from agent.src.agent.config.resolution import effective_text

    text = effective_text(path)
    raw = json.loads(text) if path.suffix == ".json" else _yaml(text)
    found = read_cases(raw.get("cases") if isinstance(raw, dict) else raw)

    chosen = tuple(getattr(check, "cases", ()) or ())
    if not chosen:
        return found
    try:
        return [found[i] for i in chosen]
    except IndexError:
        raise ValueError(
            f"the check '{check.name}' names case {max(chosen)} and the "
            f"dataset has {len(found)}"
        ) from None


def _yaml(text: str) -> Any:
    """`text` parsed as YAML, or an empty list."""
    import yaml

    return yaml.safe_load(text) or []


def run_check(
    check: Any,
    *,
    root: Path,
    search: Callable[[str, int], Sequence[str]],
    config: Any,
    document_ids: Sequence[str],
    registry: Any = None,
    k: int | None = None,
) -> tuple[Measurement, Any]:
    """Score one declared check and keep the result."""
    corpus = getattr(check, "corpus", "") or "agent"
    cases = cases_for(check, root)
    measured = measure(
        cases,
        search=search,
        corpus=corpus,
        k=k or int(getattr(config, "top_k", 8) or 8),
    )

    from agent.src.evals import usage

    usage.record(check.name)
    if registry is not None:
        registry.record_run(check.name)

    from agent.src.evals.retrieval_quality import as_result

    fingerprint = retrieval_fingerprint(config, document_ids)
    store = results_store()
    previous = _previous_fingerprint(store, measured.corpus, fingerprint)
    store.record(as_result(measured, fingerprint=fingerprint))

    if previous is None:
        return measured, None
    return measured, store.compare(
        previous, fingerprint, suite=f"retrieval:{measured.corpus}"
    )


def _previous_fingerprint(store: Any, corpus: str, current: str) -> str | None:
    """The last configuration scored on this corpus, if there is one."""
    suite = f"retrieval:{corpus}"
    for result in reversed(store.all()):
        if result.suite == suite and result.fingerprint != current:
            return str(result.fingerprint)
    return None
