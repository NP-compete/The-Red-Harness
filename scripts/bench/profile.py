"""What a benchmark run is allowed to do."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class BenchMisconfigured(ValueError):
    """A setting that would make a run meaningless rather than wrong."""


@dataclass(frozen=True)
class Bench:
    """The benchmark settings read from the config tree."""

    enabled: bool = False
    suites: tuple[str, ...] = ()
    model: str = ""
    parallel: int = 4
    results_path: str = "data/bench/results.jsonl"
    timeout_seconds: int = 900


def read_bench(raw: Any) -> Bench:
    """Read the `bench` section, falling back to defaults."""
    section = (raw or {}).get("bench") if isinstance(raw, dict) else None
    if not isinstance(section, dict):
        return Bench()

    parallel = _whole(section, "parallel", default=4)
    timeout = _whole(section, "timeout_seconds", default=900)

    return Bench(
        enabled=bool(section.get("enabled", False)),
        suites=tuple(str(s) for s in (section.get("suites") or [])),
        model=str(section.get("model") or ""),
        parallel=parallel,
        results_path=str(section.get("results_path") or Bench.results_path),
        timeout_seconds=timeout,
    )


def _whole(section: dict, field: str, *, default: int) -> int:
    """`field` as a whole number, or `default` if it is missing or bad."""
    raw = section.get(field)
    if raw is None:
        return default
    try:
        found = int(raw)
    except (TypeError, ValueError):
        raise BenchMisconfigured(
            f"bench.{field} must be a whole number, not {raw!r}"
        ) from None
    if found < 1:
        raise BenchMisconfigured(
            f"bench.{field} is {found}, which would run nothing and report a "
            f"suite that scored nothing"
        )
    return found
