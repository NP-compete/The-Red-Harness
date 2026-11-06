"""Which graded turns of an eval run a person should look at."""

from __future__ import annotations

from typing import Any, Iterable

from agent.src.evals.annotation import Graded, build_queue

MARGIN = 0.05

_FAILED = {"FAIL", "ERROR"}


def _number(value: Any) -> float | None:
    """`value` as a float, or `None` if it is not one."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence(score: float | None, threshold: float | None) -> float:
    """Derived from the distance between the score and the line it was judged against."""
    if score is None or threshold is None:
        return 1.0
    return 0.0 if abs(score - threshold) <= MARGIN else 1.0


def queue_from_turns(turns: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    """The annotation queue built from graded turns."""
    by_turn: dict[str, list[dict[str, Any]]] = {}
    for turn in turns:
        item = str(turn.get("turn_id") or "")
        if item:
            by_turn.setdefault(item, []).append(turn)

    graded = []
    for item, rows in by_turn.items():
        results = {str(row.get("result") or "").upper() for row in rows}
        scores = [_number(row.get("score")) for row in rows]
        thresholds = [_number(row.get("threshold")) for row in rows]

        failed = bool(results & _FAILED)
        if all(score is None for score in scores) and not failed:
            continue

        worst = min((score for score in scores if score is not None), default=1.0)
        confidence = min(
            _confidence(score, threshold)
            for score, threshold in zip(scores, thresholds)
        )

        graded.append(
            Graded(
                item=item,
                score=0.0 if failed else max(0.0, min(1.0, worst)),
                confidence=confidence,
                graders_disagreed=len(results) > 1,
                already_reviewed=False,
                flagged_by_person=False,
            )
        )

    return [
        {"item": entry.item, "reason": entry.reason.value}
        for entry in build_queue(graded)
    ]
