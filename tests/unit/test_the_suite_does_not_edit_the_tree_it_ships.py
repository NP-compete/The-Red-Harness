"""No test writes to the configuration this repository ships.

One fixture did. It appended a line to the real
`config/agent/runtime/agent.yaml`, then put it back on teardown —
which works right up until a run is interrupted, and this session
interrupted several. What survives then is `# touched by a test`
in the tree that gets built into the image.

It was invisible because the content always came back identical;
only the mtime moved. Teardown is not a guarantee. Writing to a
copy is.

So: a path derived from `config_root()` may be read, but not
written. Point `CONFIG_PATH` and the loader's `_base_dir` at a
`tmp_path` copy instead — `test_graph_cache_notices_the_tree.py`
shows the shape.
"""

from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"

#: Anything that changes what is on disk.
WRITES = {
    "write_text",
    "write_bytes",
    "unlink",
    "mkdir",
    "rmdir",
    "touch",
    "rename",
    "replace",
    "chmod",
    "open",
}


def _derives_from_config_root(node: ast.AST) -> bool:
    """True when this expression is built out of `config_root()`."""
    return any(
        isinstance(inner, ast.Call)
        and isinstance(inner.func, ast.Name)
        and inner.func.id == "config_root"
        for inner in ast.walk(node)
    )


def _offenders(source: str) -> list[int]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    # Names bound to something derived from config_root().
    tainted: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _derives_from_config_root(node.value):
            tainted |= {
                target.id for target in node.targets if isinstance(target, ast.Name)
            }
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and _derives_from_config_root(node.value)
        ):
            if isinstance(node.target, ast.Name):
                tainted.add(node.target.id)

    found: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in WRITES:
            continue
        receiver = node.func.value
        reaches = _derives_from_config_root(receiver) or (
            isinstance(receiver, ast.Name) and receiver.id in tainted
        )
        if reaches:
            found.append(node.lineno)
    return found


def _test_files() -> list[pathlib.Path]:
    return [
        path for path in TESTS.rglob("test_*.py") if "__pycache__" not in path.parts
    ]


def test_there_are_files_to_check():
    """A glob matching nothing would pass the assertion below."""
    assert len(_test_files()) > 100


def test_no_test_writes_into_the_shipped_config_tree():
    guilty = {
        str(path.relative_to(ROOT)): _offenders(path.read_text(encoding="utf-8"))
        for path in _test_files()
    }
    guilty = {name: lines for name, lines in guilty.items() if lines}
    assert not guilty, (
        "these write to a path derived from config_root(), which is the "
        f"tree that ships: {guilty}. Copy it to tmp_path and point "
        "CONFIG_PATH and the loader's _base_dir at the copy."
    )
