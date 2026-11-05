"""Every third-party package this code imports is one it asks for."""

from __future__ import annotations

import ast
import pathlib
import sys
import tomllib

REPO = pathlib.Path(__file__).resolve().parents[2]
TREES = (pathlib.Path("services") / "agent", pathlib.Path("scripts"))

IMPORT_TO_DISTRIBUTION = {
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "jwt": "pyjwt",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "dateutil": "python-dateutil",
    "redis": "redis",
    "psycopg": "psycopg",
    "psycopg2": "psycopg2-binary",
    "sklearn": "scikit-learn",
    "PIL": "pillow",
    "magic": "python-magic",
    "jose": "python-jose",
    "multipart": "python-multipart",
    "bs4": "beautifulsoup4",
    "fitz": "pymupdf",
}


def _declared() -> set[str]:
    data = tomllib.loads((REPO / "pyproject.toml").read_text())
    names: set[str] = set()
    for spec in data["project"]["dependencies"]:
        head = spec.split(";")[0].strip()
        for sep in (" @ ", "==", ">=", "<=", "~=", "!=", ">", "<", "["):
            if sep in head:
                head = head.split(sep)[0]
        names.add(head.strip().lower().replace("_", "-"))
    return names


def _imported() -> dict[str, set[str]]:
    """Top-level imported names, mapped to the files importing them."""
    found: dict[str, set[str]] = {}
    for tree in TREES:
        for path in (REPO / tree).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                parsed = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            optional: set[int] = set()
            for node in ast.walk(parsed):
                if isinstance(node, ast.Try) and any(
                    isinstance(h.type, ast.Name)
                    and h.type.id == "ImportError"
                    or isinstance(h.type, ast.Tuple)
                    and any(
                        isinstance(e, ast.Name) and e.id == "ImportError"
                        for e in h.type.elts
                    )
                    for h in node.handlers
                ):
                    for child in ast.walk(node):
                        if hasattr(child, "lineno"):
                            optional.add(child.lineno)

            for node in ast.walk(parsed):
                if getattr(node, "lineno", None) in optional:
                    continue
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    top = name.split(".")[0]
                    if top:
                        found.setdefault(top, set()).add(str(path.relative_to(REPO)))
    return found


def _is_ours(name: str) -> bool:
    # `agent` lives under services/ now, so a repo-root check alone
    # reads the first-party package as an undeclared dependency.
    return any(
        (base / name).is_dir() or (base / f"{name}.py").is_file()
        for base in (REPO, REPO / "services")
    )


PLATFORM_IMPLIED = frozenset(
    {
        "fastapi",
        "starlette",
        "uvicorn",
        "sqlalchemy",
        "psycopg_pool",
        "prometheus_client",
        "langchain",
        "langchain_core",
        "openai",
        "google",
        "opentelemetry",
        "pymongo",
        "pydantic_core",
        "typing_extensions",
    }
)


def test_every_imported_package_is_declared() -> None:
    declared = _declared()
    missing: dict[str, set[str]] = {}

    for name, files in _imported().items():
        if name in sys.stdlib_module_names or _is_ours(name):
            continue
        if name in PLATFORM_IMPLIED:
            continue
        distribution = IMPORT_TO_DISTRIBUTION.get(name, name)
        if distribution.lower().replace("_", "-") in declared:
            continue
        missing[name] = files

    assert not missing, (
        "imported but not in pyproject dependencies, and not implied by the "
        "platform — each of these works only while something else happens "
        "to pull it in, and breaks on somebody else's release with no "
        "change here:\n"
        + "\n".join(
            f"  {name}: {', '.join(sorted(files)[:3])}"
            for name, files in sorted(missing.items())
        )
    )
