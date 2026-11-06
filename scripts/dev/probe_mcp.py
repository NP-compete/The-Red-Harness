"""Drive the /mcp routes against the running cluster."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services"))

BASE = "http://localhost:8081"
HOST = "agent.localhost"
MCP_JSON = "config/agent/integrations/mcp.json"

failures: list[str] = []


def call(method: str, route: str, body: dict | None = None) -> tuple[int, Any, str]:
    """Call the agent and return the status, decoded body and content type."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + route, data=data, method=method)
    request.add_header("Host", HOST)
    if data:
        request.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as answer:
            raw = answer.read()
            kind = answer.headers.get("content-type", "")
    except urllib.error.HTTPError as failed:
        raw = failed.read()
        kind = failed.headers.get("content-type", "")
        return failed.code, _decode(raw, kind), kind
    return 200, _decode(raw, kind), kind


def _decode(raw: bytes, kind: str) -> Any:
    """Decode a response body as JSON when the content type says so."""
    if raw and kind.startswith("application/json"):
        return json.loads(raw)
    return raw


def roundtrips(name: str, model: type[BaseModel], body: Any) -> None:
    """Report whether `body` survives a round trip through `model`."""
    dumped = model.model_validate(body).model_dump(
        mode="json", by_alias=True, exclude_unset=True
    )
    if dumped == body:
        print(f"  {name:<34} round-trips")
        return
    failures.append(name)
    print(f"  {name:<34} DOES NOT round-trip", file=sys.stderr)
    print(f"    sent     {json.dumps(body)[:300]}", file=sys.stderr)
    print(f"    declared {json.dumps(dumped)[:300]}", file=sys.stderr)


def configured() -> None:
    """Probe the configured MCP servers, status and connections."""
    from agent.aegra.mcp_routes import (
        McpConnectionsOut,
        McpServersOut,
        McpStatusOut,
    )

    print("/mcp, from this deployment's own configuration")
    code, servers, _ = call("GET", "/mcp/servers")
    if code != 200:
        raise SystemExit(f"/mcp/servers: {code} {servers}")
    names = [one["name"] for one in servers["servers"]]
    if not names:
        raise SystemExit("no MCP servers configured — nothing to check a shape against")
    print(f"  {len(names)} configured, {servers['enabled_count']} enabled")
    roundtrips("GET  /mcp/servers", McpServersOut, servers)

    code, connections, _ = call("GET", "/mcp/oauth/connections")
    listed = [one["mcp_name"] for one in connections["connections"]]
    if not listed:
        raise SystemExit("no connection records — the shape would go unchecked")
    roundtrips("GET  /mcp/oauth/connections", McpConnectionsOut, connections)

    for name in names:
        code, status, _ = call("GET", f"/mcp/{name}/status")
        if code != 200:
            raise SystemExit(f"/mcp/{name}/status: {code} {status}")
        roundtrips(f"GET  /mcp/{name}/status", McpStatusOut, status)


def icon_is_not_json() -> None:
    """The icon route is declared as an image now; check it sends one."""
    code, _body, kind = call("GET", "/mcp/atlan/icon")
    if code == 404:
        print("  no icon cached for atlan; media type unchecked")
        return
    if kind.startswith("application/json"):
        failures.append("/mcp/{name}/icon")
        print(
            f"  /mcp/atlan/icon answered {kind}, and the contract now says image/*",
            file=sys.stderr,
        )
        return
    print(f"  /mcp/atlan/icon sends {kind}, as declared")


def editing_adds_a_server() -> None:
    """An edit to `mcp.json` reaches the loader, and so does a new file."""
    from agent.aegra.mcp_routes import McpServersOut

    print("/mcp/servers, after an edit")
    code, current, _ = call("GET", f"/config/file?path={MCP_JSON}")
    if code != 200:
        raise SystemExit(f"cannot read {MCP_JSON}: {code} {current}")
    text = current["content"]
    if "strand-c-probe" in text:
        raise SystemExit("a previous run left its server behind")
    marker = '"mcpServers": {'
    if marker not in text:
        raise SystemExit("mcp.json has no mcpServers object to add to")
    entry = (
        '\n    "strand-c-probe": {\n'
        '      "url": "https://example.invalid/mcp",\n'
        '      "display_name": "Strand C Probe",\n'
        '      "description": "Added by a probe; removed again.",\n'
        '      "transport": "streamable_http",\n'
        '      "enabled": true\n'
        "    },"
    )
    changed = text.replace(marker, marker + entry, 1)

    code, written, _ = call(
        "PUT",
        "/config/edit",
        {
            "path": MCP_JSON,
            "content": changed,
            "base_version": current["version"],
        },
    )
    if code != 200:
        raise SystemExit(f"could not add a server: {code} {written}")

    try:
        code, servers, _ = call("GET", "/mcp/servers")
        names = [one["name"] for one in servers["servers"]]
        if "strand-c-probe" not in names:
            raise SystemExit(
                "the edit was accepted and the agent does not list the server — "
                "the overlay is not reaching the loader"
            )
        print(f"  the agent now lists {len(names)} servers, mine among them")
        roundtrips("GET  /mcp/servers (after edit)", McpServersOut, servers)
    finally:
        call("POST", "/config/adopt-baseline", {"path": MCP_JSON})
        code, servers, _ = call("GET", "/mcp/servers")
        if "strand-c-probe" in [one["name"] for one in servers["servers"]]:
            raise SystemExit("the override was dropped and the server is still listed")
        print("  override dropped; the agent lists the tree's servers again")


def main() -> int:
    """Run every MCP probe in order."""
    configured()
    icon_is_not_json()
    editing_adds_a_server()

    if failures:
        print(
            f"\n{len(failures)} response(s) do not match the declared shape",
            file=sys.stderr,
        )
        return 1
    print("\nevery response checked matches the shape its route declares")
    print("not checked, no reachable MCP server: capabilities, inventory,")
    print("tools/list, tools/call, resources/{list,templates/list,read},")
    print(
        "connect, reregister, disconnect, the OAuth callback, and\n/mcp/server (integrations/mcp_server.yaml is outside the edit allowlist)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
