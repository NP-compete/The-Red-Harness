"""Contract tests for the routes `platform/template-ui` depends on."""

from __future__ import annotations

import pytest
from aegra_api.main import create_app
from fastapi.routing import APIRoute

REQUIRED_ROUTES: list[tuple[str, str]] = [
    ("/threads", "POST"),
    ("/threads/{thread_id}/runs/stream", "POST"),
    ("/threads/{thread_id}/state", "GET"),
    ("/health", "GET"),
    ("/feedback", "POST"),
    ("/mcp/{mcp_name}/connect", "POST"),
    ("/mcp/{mcp_name}/resources/list", "POST"),
    ("/mcp/{mcp_name}/tools/list", "POST"),
    ("/admin/config", "GET"),
]


@pytest.fixture(scope="module")
def route_table() -> set[tuple[str, str]]:
    """Every (path, method) pair the agent actually serves."""
    table: set[tuple[str, str]] = set()

    def walk(routes: list) -> None:
        for route in routes:
            if isinstance(route, APIRoute):
                for method in route.methods:
                    table.add((route.path, method))
                continue
            nested = getattr(route, "original_router", None)
            if nested is not None:
                walk(list(nested.routes))
            elif getattr(route, "routes", None):
                walk(list(route.routes))

    walk(list(create_app().routes))
    return table


@pytest.mark.parametrize(("path", "method"), REQUIRED_ROUTES)
def test_route_required_by_ui_exists(
    route_table: set[tuple[str, str]], path: str, method: str
) -> None:
    assert (path, method) in route_table, (
        f"template-ui's proxy calls {method} {path}, which this service no "
        f"longer serves. Update template-ui/src/server/router/proxy.router.ts "
        f"in the same change, or restore the route."
    )


def test_run_create_accepts_a_resume_command() -> None:
    """HITL resume depends on `command` surviving on the run payload."""
    from aegra_api.models.runs import RunCreate

    run = RunCreate(assistant_id="agent", command={"resume": [{"type": "accept"}]})

    assert run.command == {"resume": [{"type": "accept"}]}
    assert run.input is None


def test_no_v1_stream_route_is_reintroduced(
    route_table: set[tuple[str, str]],
) -> None:
    """Guards the specific drift that went unnoticed for months."""
    assert ("/v1/stream", "POST") not in route_table
