#!/usr/bin/env python
"""Cut comments and docstrings back to the minimum."""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import token
import tokenize
from pathlib import Path

DIRECTIVE = re.compile(
    r"#\s*(noqa|type:|pragma|fmt:|isort:|mypy:|ruff:|nosec|pylint|coding[:=])", re.I
)

#: Docstrings that are the point of the file, not a label on it.
#: The four `aegra/` modules are dormant — `test_dormant_modules_say_so`
#: requires each to explain that it is unused and why it is kept, so a
#: trim to the first line is what that test exists to catch. An earlier
#: run of this script listed the same four names under `src/agent/`,
#: which are different files, and flattened these.
KEEP_DOCSTRINGS = {
    "services/agent/src/agent/errors.py",
    "services/agent/src/agent/converters.py",
    "services/agent/src/agent/state.py",
    "services/agent/src/agent/serialization.py",
    "services/agent/aegra/state.py",
    "services/agent/aegra/nodes.py",
    "services/agent/aegra/converters.py",
    "services/agent/aegra/serialization.py",
}


def _summary(value: str) -> str:
    """The first line of an already-decoded docstring."""
    first = next((ln.strip() for ln in value.strip().splitlines() if ln.strip()), "")
    return first.replace('"""', "'''")


def trim(source: str, *, keep_docstrings: bool) -> str:
    """`source` with its comments removed, optionally keeping docstrings."""
    out: list[str] = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source

    docs: dict[tuple[int, int], str] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            docs[(first.value.lineno, first.value.col_offset)] = first.value.value

    lines = source.splitlines(keepends=True)
    drop: set[int] = set()
    replace: dict[int, str] = {}

    for tok in toks:
        if tok.type == tokenize.COMMENT:
            if (
                DIRECTIVE.search(tok.string)
                or tok.start[1] == 0
                and tok.line.startswith("#!")
            ):
                continue
            row = tok.start[0]
            before = tok.line[: tok.start[1]]
            if before.strip() == "":
                drop.add(row)
            else:
                replace[row] = before.rstrip() + "\n"
        elif tok.type == token.STRING and tok.start in docs and not keep_docstrings:
            first, last = tok.start[0], tok.end[0]
            if last > first:
                indent = " " * tok.start[1]
                replace[first] = f'{indent}"""{_summary(docs[tok.start])}"""\n'
                drop.update(range(first + 1, last + 1))

    for i, line in enumerate(lines, 1):
        if i in drop:
            continue
        out.append(replace.get(i, line))

    text = "".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(\n\s*\n)(\s*)(\)|\]|\})", r"\n\2\3", text)
    return text


def main() -> int:
    """Trim comments from the Python files under the given roots."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--apply", action="store_true", help="write the files")
    ap.add_argument("--ext", default=".py")
    args = ap.parse_args()

    before = after = files = 0
    for root in args.roots:
        for path in sorted(Path(root).rglob(f"*{args.ext}")):
            if "__pycache__" in path.parts or ".venv" in path.parts:
                continue
            src = path.read_text(encoding="utf-8", errors="ignore")
            rel = str(path)
            new = trim(src, keep_docstrings=any(k in rel for k in KEEP_DOCSTRINGS))
            if new == src:
                continue
            files += 1
            before += len(src.splitlines())
            after += len(new.splitlines())
            if args.apply:
                path.write_text(new, encoding="utf-8")

    verb = "trimmed" if args.apply else "would trim"
    print(
        f"{verb} {files} files: {before:,} -> {after:,} lines "
        f"({before - after:,} removed)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
