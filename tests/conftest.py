"""Root test configuration and shared fixtures."""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _import_everything_that_reads_settings_at_import_time() -> None:
    """Import, once and early, every module that reads `settings`.

    Dozens of modules do `_MAX_SOMETHING = settings.SOMETHING` at
    module level, and `graph.agent()` imports many of them lazily,
    inside the call. So a test that patches
    `agent.src.settings.settings` with a MagicMock and then triggers
    the *first* import of one of them binds a MagicMock into a module
    constant for the rest of the session — `int > MagicMock`,
    `logging.setLevel(MagicMock)`, a pydantic field that wanted a str.

    Which test that is depends entirely on ordering. Seventeen of
    `test_graph.py` passed in a full local run and failed in the
    pipeline, and failed locally the moment that file ran on its own:
    the suite was green because some earlier test happened to import
    these first. That is not a property to rely on, and it is not one
    a reviewer can see.

    Found rather than listed. A hand-written list of module names is
    the kind of thing that is correct on the day it is written.
    """
    import importlib

    source_root = Path(_PROJECT_ROOT) / "services"
    marker = "from agent.src.settings import settings"
    for path in sorted((source_root / "agent").rglob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            if marker not in path.read_text(encoding="utf-8"):
                continue
        except OSError:
            continue
        dotted = ".".join(path.relative_to(source_root).with_suffix("").parts)
        try:
            importlib.import_module(dotted)
        except Exception:  # noqa: BLE001 - an optional dependency, not our problem here
            # A module that cannot be imported at all will fail in the
            # test that needs it, with a better message than this.
            continue


_import_everything_that_reads_settings_at_import_time()


@pytest.fixture(autouse=True)
def _no_overlay_leaks_out():
    """Clear the process-global config overlay after every test."""
    yield
    from agent.src.agent.config import resolution

    resolution.use_overlay(None)


@pytest.fixture()
def mock_llm():
    """Return a MagicMock that behaves like a LangChain BaseChatModel."""
    from langchain_core.messages import AIMessage

    llm = MagicMock()
    default_response = AIMessage(content="mock llm response", id="mock_msg_1")

    llm.invoke.return_value = default_response
    llm.ainvoke = AsyncMock(return_value=default_response)
    llm.bind_tools.return_value = llm
    llm.with_structured_output.return_value = llm
    llm.model_name = "mock-model"

    return llm


@pytest.fixture()
def mock_db_uri() -> str:
    """Return a fake Postgres URI for unit tests (no real connection)."""
    return "postgresql://test:test@localhost:5432/testdb"


@pytest.fixture()
def mock_async_connection():
    """Return a mock ``psycopg.AsyncConnection`` context manager."""
    conn = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchall = AsyncMock(return_value=[])
    cursor.fetchone = AsyncMock(return_value=None)
    cursor.rowcount = 0
    conn.execute = AsyncMock(return_value=cursor)
    conn.commit = AsyncMock()

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)

    conn._cursor = cursor
    conn._ctx = ctx
    return conn


@pytest.fixture()
def mock_checkpointer():
    """Return a mock async checkpointer (PostgresSaver-like)."""
    cp = AsyncMock()
    cp.setup = AsyncMock()
    cp.__aenter__ = AsyncMock(return_value=cp)
    cp.__aexit__ = AsyncMock(return_value=False)
    return cp


@pytest.fixture()
def test_settings():
    """Return a Settings instance with safe test defaults."""
    from agent.src.settings import Settings

    return Settings(
        AGENT_HOST="127.0.0.1",
        AGENT_PORT=5099,
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
        POSTGRES_USER="test",
        POSTGRES_PASSWORD="test",
        POSTGRES_DB="testdb",
        PYTHON_LOG_LEVEL="WARNING",
    )


@pytest.fixture()
def mock_agent_config():
    """Return a mock agent_config with a minimal orchestrator config."""
    config = MagicMock()
    config.get_orchestrator_config.return_value = {
        "name": "test-orchestrator",
        "model": "mock-model",
        "body": "You are a test agent.",
        "skill_paths": [],
        "tools": [],
    }
    config.resolve_tools.return_value = []
    return config


@pytest.fixture()
def mock_mcp_tools() -> list[Any]:
    """Return an empty list of MCP tools for unit tests."""
    return []


@pytest.fixture()
def llm_cassette(request):
    """Record/replay HTTP traffic for one test."""
    from tests.fixtures.cassette import (
        CASSETTE_DIR,
        Cassette,
        CassetteTransport,
        cassette_mode,
    )

    mode = cassette_mode()
    cassette = Cassette(CASSETTE_DIR / f"{request.node.name}.json", mode)

    def _client(**kwargs):
        return httpx.AsyncClient(transport=CassetteTransport(cassette), **kwargs)

    yield _client

    if mode == "record":
        cassette.save()


@pytest.fixture()
def fake_clock(monkeypatch):
    """A clock the test advances by hand."""
    from tests.fixtures.clock import FakeClock, install

    clock = FakeClock()
    install(monkeypatch, clock)
    return clock


@pytest.fixture(autouse=True)
def _reset_shared_db_pool():
    """Stop a live pool leaking from one test into the next."""
    import agent.src.db.pool as shared_pool

    shared_pool._pool = None
    yield
    shared_pool._pool = None


@pytest.fixture(autouse=True)
def _no_real_datastores(request, monkeypatch):
    """Point unit tests at addresses nothing is listening on."""
    if request.node.get_closest_marker("real_datastores"):
        yield
        return

    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    monkeypatch.setenv("POSTGRES_HOST", "127.0.0.1")
    monkeypatch.setenv("POSTGRES_PORT", "1")

    import agent.aegra.redis as redis_mod

    monkeypatch.setattr(redis_mod, "REDIS_URL", "redis://127.0.0.1:1/0")
    monkeypatch.setattr(redis_mod, "_client", None)
    monkeypatch.setattr(redis_mod, "_async_client", None)
    monkeypatch.setattr(redis_mod, "_async_client_loop", None)

    yield

    redis_mod._client = None
    redis_mod._async_client = None
    redis_mod._async_client_loop = None


@pytest.fixture(autouse=True)
def _forget_tool_shapes():
    """Start each test with no memory of any tool's shape."""
    from agent.src.security import tool_preflight

    tool_preflight._SHAPES = None
    yield
    tool_preflight._SHAPES = None


@pytest.fixture(autouse=True)
def _forget_deliveries():
    """Start each test with nothing already delivered."""
    from agent.src.channels import dispatch

    dispatch._DELIVERED.clear()
    yield
    dispatch._DELIVERED.clear()


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    from datetime import date

    from tests.quarantine import apply_quarantine, load

    try:
        entries = load()
    except Exception:  # noqa: BLE001
        return
    if entries:
        apply_quarantine(items, entries, date.today())
