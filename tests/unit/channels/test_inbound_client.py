"""The inbound door, driven by a real client rather than a mock of one."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


pytest.importorskip("mcp", reason="the client library is not installed")

REPO = Path(__file__).resolve().parents[3]

DOOR_OPEN = """\
mcp_server:
  enabled: true
  auth:
    mode: service_token
  tools:
    - name: ask
      description: "Ask this agent a question and get an answer"
      scope: read
"""


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _answering(port: int, *, within: float = 60.0) -> bool:
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        with socket.socket() as probe:
            probe.settimeout(0.5)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


@pytest.fixture(scope="module")
def door(tmp_path_factory) -> str:
    """A server with the door open, on a port nobody else has."""
    tree = tmp_path_factory.mktemp("config")
    (tree / "integrations").mkdir()
    (tree / "integrations" / "mcp_server.yaml").write_text(DOOR_OPEN)
    shipped = REPO / "config" / "agent"
    (tree / "PROMPT.md").write_text((shipped / "PROMPT.md").read_text())
    (tree / "integrations" / "mcp.json").write_text("{}")
    (tree / "runtime").mkdir()
    (tree / "runtime" / "agent.yaml").write_text(
        (shipped / "runtime" / "agent.yaml").read_text()
    )

    port = _free_port()
    environment = {**os.environ, "CONFIG_PATH": str(tree), "AGENT_PORT": str(port)}
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "agent.aegra.http_app:app",
            "--port",
            str(port),
            "--log-level",
            "error",
        ],
        cwd=REPO,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not _answering(port):
            pytest.skip("the server did not start in time")
        yield f"http://127.0.0.1:{port}/mcp/server"
    finally:
        server.terminate()
        server.wait(timeout=30)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAStandardClient:
    async def test_it_can_open_a_session(self, door):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(door) as (read, write, _):
            async with ClientSession(read, write) as session:
                assert await session.initialize()

    async def test_the_agent_names_itself(self, door):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(door) as (read, write, _):
            async with ClientSession(read, write) as session:
                found = await session.initialize()
        assert found.serverInfo.name

    async def test_the_client_and_the_agent_agree_on_a_version(self, door):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(door) as (read, write, _):
            async with ClientSession(read, write) as session:
                found = await session.initialize()
        assert found.protocolVersion

    async def test_it_lists_the_declared_tool(self, door):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(door) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                found = await session.list_tools()
        assert [tool.name for tool in found.tools] == ["ask"]

    async def test_the_client_can_read_the_argument_schema(self, door):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(door) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                found = await session.list_tools()
        assert "question" in found.tools[0].inputSchema["properties"]

    async def test_a_tool_nobody_declared_is_refused(self, door):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(door) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                found = await session.call_tool(
                    "drop_everything", {"question": "hello"}
                )
        assert found.isError
