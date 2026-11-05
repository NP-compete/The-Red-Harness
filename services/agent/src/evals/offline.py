"""The checks a build can run without a model (E22-T2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

OFFLINE_KINDS = ("retrieval",)


@dataclass
class Report:
    """What the offline evals ran, skipped, and found wrong."""

    ran: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    problems: list[dict[str, str]] = field(default_factory=list)
    regressions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether nothing was wrong and nothing regressed."""
        return not self.problems and not self.regressions

    def say(self) -> str:
        """The report as a build reads it: what ran, what did not, why."""
        lines = []
        for row in self.ran:
            against = (
                ""
                if row["against_previous"] is None
                else f" ({row['against_previous']})"
            )
            lines.append(
                f"  ran      {row['name']}: recall {row['recall']:.3f} "
                f"over {row['cases']} case(s){against}"
            )
        for row in self.skipped:
            lines.append(f"  skipped  {row['name']}: {row['why']}")
        for row in self.problems:
            lines.append(f"  PROBLEM  {row['where']}: {row['what']}")
        for row in self.regressions:
            lines.append(
                f"  WORSE    {row['name']}: recall moved {row['difference']:+.3f}"
            )
        if not lines:
            lines.append("  nothing is declared")
        return "\n".join(lines)


def run_offline(
    root: Path,
    *,
    search_for: Any,
    config: Any,
    document_ids_for: Any,
) -> Report:
    """Score every check this build can score, and say what it skipped."""
    from agent.src.evals.declared import load_checks
    from agent.src.evals.retrieval_runner import run_check

    report = Report()
    checks, problems = load_checks(root)
    report.problems.extend(problems)

    for check in checks:
        if check.kind not in OFFLINE_KINDS:
            report.skipped.append(
                {
                    "name": check.name,
                    "why": (
                        f"a {check.kind} check is scored by a judge "
                        f"({check.judge or 'unnamed'}), and a build has no model"
                    ),
                }
            )
            continue

        try:
            measured, comparison = run_check(
                check,
                root=root,
                search=search_for(check.corpus),
                config=config,
                document_ids=document_ids_for(check.corpus),
            )
        except ValueError as refused:
            report.problems.append({"where": check.source, "what": str(refused)})
            continue

        report.ran.append(
            {
                "name": check.name,
                "corpus": measured.corpus,
                "recall": measured.recall,
                "precision": measured.precision,
                "cases": len(measured.cases),
                "against_previous": (
                    None
                    if comparison is None
                    else f"{comparison.difference:+.3f}"
                    + (
                        " and that is beyond the noise"
                        if comparison.significant
                        else ""
                    )
                ),
            }
        )

        if (
            comparison is not None
            and comparison.significant
            and comparison.difference < 0
        ):
            report.regressions.append(
                {"name": check.name, "difference": comparison.difference}
            )

    return report
