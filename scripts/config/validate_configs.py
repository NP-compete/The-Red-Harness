"""Check a directory of configuration trees against this build."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_SERVICES = str(REPO_ROOT / "services")
if _SERVICES not in sys.path:
    sys.path.insert(0, _SERVICES)

from agent.src.agent.config.paths import _CANDIDATES  # noqa: E402
from agent.src.agent.config.validate import validate_config  # noqa: E402


@dataclass(frozen=True)
class TreeResult:
    """One config tree and whatever is wrong with it."""

    name: str
    path: Path
    problems: list[str]

    @property
    def ok(self) -> bool:
        """Whether the tree validated cleanly."""
        return not self.problems


def _is_tree(path: Path) -> bool:
    """Whether a directory holds an agent configuration."""
    return path.is_dir() and any((path / rel).is_file() for rel in _CANDIDATES["agent"])


def trees_under(root: Path) -> list[Path]:
    """Every configuration tree in `root`, or `root` itself if it is one."""
    if _is_tree(root):
        return [root]
    return sorted(child for child in root.iterdir() if _is_tree(child))


def check_trees(root: Path) -> list[TreeResult]:
    """Load each tree against the current models and say what failed."""
    results = []
    for tree in trees_under(root):
        report = validate_config(tree)
        results.append(
            TreeResult(
                name=tree.name,
                path=tree,
                problems=[f.render().strip() for f in report.errors],
            )
        )
    return results


def main(argv: list[str] | None = None) -> int:
    """Validate every config tree under the given directory."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: validate_configs.py <directory>", file=sys.stderr)
        return 2

    root = Path(args[0]).expanduser()
    if not root.is_dir():
        print(f"{root} is not a directory", file=sys.stderr)
        return 2

    results = check_trees(root)
    if not results:
        print(f"No configuration trees found under {root}", file=sys.stderr)
        return 2

    for result in results:
        print(f"{'PASS' if result.ok else 'FAIL'}  {result.name}")
        for problem in result.problems:
            print(f"        {problem}")

    failed = [r for r in results if not r.ok]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
