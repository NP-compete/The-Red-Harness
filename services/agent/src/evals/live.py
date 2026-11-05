"""Scoring a declared check against a running agent (E22-T3)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.src.evals.judge import Criterion, Judgement, Rubric, score_answer
from agent.src.evals.registry import Check


@dataclass(frozen=True)
class Case:
    """One question from a dataset, and what must be true of the answer."""

    id: int
    prompt: str
    assertions: tuple[str, ...]


def load_cases(root: Path, check: Check) -> list[Case]:
    """The cases this check names, or a `ValueError` saying which is missing."""
    if not check.dataset:
        raise ValueError(f"check '{check.name}' names no dataset")
    path = root / check.dataset
    raw = json.loads(path.read_text(encoding="utf-8"))
    by_id = {int(e["id"]): e for e in raw.get("evals") or []}

    wanted = check.cases or tuple(sorted(by_id))
    missing = [i for i in wanted if i not in by_id]
    if missing:
        raise ValueError(
            f"check '{check.name}': {check.dataset} has no case "
            f"{', '.join(str(i) for i in missing)}"
        )

    cases: list[Case] = []
    for case_id in wanted:
        entry = by_id[case_id]
        assertions = tuple(str(a) for a in entry.get("assertions") or ())
        if not assertions:
            raise ValueError(
                f"check '{check.name}': case {case_id} of {check.dataset} "
                "asserts nothing, so passing it would mean nothing"
            )
        cases.append(
            Case(id=case_id, prompt=str(entry["prompt"]), assertions=assertions)
        )
    return cases


def rubric_for(case: Case) -> Rubric:
    """A rubric requiring every assertion of `case`."""
    return Rubric(
        criteria=tuple(
            Criterion(name=str(n), weight=1.0, required=True)
            for n in range(1, len(case.assertions) + 1)
        ),
        pass_mark=1.0,
    )


def verdict_prompt(case: Case, answer: str) -> str:
    """What to ask about an answer."""
    numbered = "\n".join(
        f"{n}. {text}" for n, text in enumerate(case.assertions, start=1)
    )
    return (
        "You are grading another assistant's reply. Answer only about what "
        "the reply says — do not be generous, and do not reward intent.\n\n"
        f"The question it was asked:\n{case.prompt}\n\n"
        f"Its reply:\n{answer}\n\n"
        f"For each statement below, is it true of that reply?\n{numbered}\n\n"
        "Reply with one JSON object and nothing else: the keys are the "
        'numbers as strings, the values are true or false. Example: {"1": '
        'true, "2": false}'
    )


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def read_verdict(text: str, rubric: Rubric) -> dict[str, bool]:
    """The judge's answer, as the rubric's criteria."""
    body = text.strip()
    fenced = _FENCE.search(body)
    if fenced:
        body = fenced.group(1).strip()
    else:
        start, end = body.find("{"), body.rfind("}")
        if start != -1 and end > start:
            body = body[start : end + 1]

    try:
        raw = json.loads(body)
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}

    asked = {c.name for c in rubric.criteria}
    return {
        str(k): bool(v)
        for k, v in raw.items()
        if str(k) in asked and isinstance(v, bool)
    }


@dataclass(frozen=True)
class Scored:
    """One case, the answer it got, and how it was judged."""

    case: Case
    answer: str
    judgement: Judgement

    def say(self) -> str:
        """The one-line account of how this case went."""
        if not self.judgement.reliable:
            return f"case {self.case.id}: not scored — {self.judgement.reason}"
        if self.judgement.passed:
            return (
                f"case {self.case.id}: passed {len(self.case.assertions)} assertion(s)"
            )
        unmet = ", ".join(
            self.case.assertions[int(n) - 1] for n in self.judgement.unmet
        )
        return f"case {self.case.id}: failed — {unmet}"


def run_case(
    case: Case,
    *,
    ask: Callable[[str], str],
    judge: Callable[..., Any],
) -> Scored:
    """Ask the agent, then ask the judge, then score what came back."""
    answer = ask(case.prompt)
    rubric = rubric_for(case)
    verdict = read_verdict(judge(verdict_prompt(case, answer)), rubric)
    return Scored(
        case=case, answer=answer, judgement=score_answer(verdict, rubric=rubric)
    )
