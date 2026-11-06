"""The checks this deployment declares, from a terminal (E28-T8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class Transport(Protocol):
    """Makes requests to the agent on the CLI's behalf."""

    def get(self, path: str) -> tuple[int, Any]:
        """GET `path` and return the status and decoded body."""
        ...

    def post(self, path: str, body: dict | None = None) -> tuple[int, Any]:
        """POST `body` to `path` and return the status and decoded body."""
        ...


class EvalFailed(RuntimeError):
    """The agent would not, or could not, answer."""


class NotScorable(EvalFailed):
    """The check cannot produce a number here."""


@dataclass(frozen=True)
class Check:
    """One eval check as the agent reports it."""

    name: str
    group: str
    decides: str = ""
    judge: str = ""
    kind: str = "judged"
    corpus: str = ""


@dataclass(frozen=True)
class Usage:
    """How often each check has run, and which never have."""

    rows: list[tuple[str, int]] = field(default_factory=list)
    unused: list[str] = field(default_factory=list)

    @property
    def any_runs(self) -> bool:
        """Whether any check has run at all."""
        return any(count for _name, count in self.rows)


def checks(*, transport: Transport) -> list[Check]:
    """Every eval check the agent knows about."""
    status, payload = transport.get("/evals/checks")
    if status != 200 or not isinstance(payload, dict):
        raise EvalFailed(f"Could not read the checks ({status})")
    return [
        Check(
            name=str(one.get("name") or ""),
            group=str(one.get("group") or ""),
            decides=str(one.get("decides") or ""),
            judge=str(one.get("judge") or ""),
            kind=str(one.get("kind") or "judged"),
            corpus=str(one.get("corpus") or ""),
        )
        for one in (payload.get("checks") or [])
        if isinstance(one, dict)
    ]


def usage(*, transport: Transport) -> Usage:
    """The agent's report of how often each check has run."""
    status, payload = transport.get("/evals/checks/usage")
    if status != 200 or not isinstance(payload, dict):
        raise EvalFailed(f"Could not read the usage report ({status})")
    return Usage(
        rows=[
            (str(one.get("name") or ""), int(one.get("runs") or 0))
            for one in (payload.get("rows") or [])
            if isinstance(one, dict)
        ],
        unused=[str(one) for one in (payload.get("unused") or [])],
    )


def why_unused(found: Usage) -> str:
    """What a zero means here, which is not always the same thing."""
    if not found.unused:
        return ""
    if not found.any_runs:
        return (
            "Nothing has run here at all, so these zeros say nothing about "
            "whether the checks are needed. Read this on a deployment that "
            "runs them before deleting any."
        )
    return (
        "Some checks have run and these have not — which is the evidence "
        "E22's pruning rule asks for, on this deployment."
    )


def score(name: str, *, transport: Transport) -> dict[str, Any]:
    """Run one retrieval check and report what it scored."""
    status, payload = transport.post("/v1/eval/retrieval", {"check": name})
    if status == 404:
        raise NotScorable(_why(payload) or f"{name} has nothing to score here")
    if status == 422:
        raise EvalFailed(f"{name} cannot be run: {_why(payload)}")
    if status not in (200, 201) or not isinstance(payload, dict):
        raise EvalFailed(f"Could not run {name} ({status}): {_why(payload)}")
    return payload


def _why(payload: Any) -> str:
    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("detail") or "")
    return ""
