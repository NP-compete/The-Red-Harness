"""The quality checks a deployment runs, and how often they are used."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    """One eval check: what it measures and which decision it informs."""

    name: str
    group: str
    decides: str
    judge: str = ""
    dataset: str = ""
    cases: tuple[int, ...] = ()
    kind: str = "judged"
    needs: tuple[str, ...] = ()
    corpus: str = ""
    source: str = ""

    def __post_init__(self) -> None:
        """Reject a check that does not say what it decides or has an unknown kind."""
        if not self.decides.strip():
            raise ValueError(f"check '{self.name}' must say what decision it informs")
        if self.kind not in ("judged", "retrieval"):
            raise ValueError(
                f"check '{self.name}' has kind '{self.kind}'; the kinds are "
                "'judged' and 'retrieval'"
            )
        if self.kind == "retrieval" and not self.corpus.strip():
            raise ValueError(
                f"the retrieval check '{self.name}' must name the corpus it "
                "measures — a score across every corpus at once is a number "
                "nobody can act on"
            )


class CheckRegistry:
    """Every known check, with a count of how often each has run."""

    def __init__(self, checks: list[Check]) -> None:
        """Index `checks` by name, rejecting duplicates."""
        names = [c.name for c in checks]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(f"duplicate check names: {', '.join(sorted(duplicates))}")

        self._checks = {c.name: c for c in checks}
        self._runs: Counter[str] = Counter()

    def groups(self) -> tuple[str, ...]:
        """Every group that has at least one check, sorted."""
        return tuple(sorted({c.group for c in self._checks.values()}))

    def in_group(self, group: str) -> tuple[Check, ...]:
        """The checks in `group`, sorted by name."""
        return tuple(
            sorted(
                (c for c in self._checks.values() if c.group == group),
                key=lambda c: c.name,
            )
        )

    def get(self, name: str) -> Check:
        """One check by name, or `KeyError` naming it."""
        return self._checks[name]

    def record_run(self, name: str) -> None:
        """Count one run of the check named `name`."""
        if name not in self._checks:
            raise KeyError(name)
        self._runs[name] += 1

    def usage(self) -> dict[str, int]:
        """How many times each check has run."""
        return {name: self._runs[name] for name in self._checks}

    def unused(self) -> tuple[str, ...]:
        """Checks that have never run, sorted."""
        return tuple(sorted(name for name in self._checks if self._runs[name] == 0))
