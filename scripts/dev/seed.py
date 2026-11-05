"""The fixture state a developer loses on every restart (E27-T4)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

_SERVICES = str(REPO_ROOT / "services")
if _SERVICES not in sys.path:
    sys.path.insert(0, _SERVICES)

AGENT = os.environ.get("SEED_AGENT_URL", "http://localhost:5002")
AGENT_HOST = os.environ.get("SEED_AGENT_HOST")
WHO = "dev-user"
SPACE = "Billing migration"
GROUP = "cn=billing,ou=groups,dc=example,dc=com"
THREAD = "Seeded conversation"
MCP = "unstructured-data"

MESSAGES = (
    "the overnight ingest looks short by about 4,000 rows",
    "@orchestrator can you check which partitions are missing?",
)

OPENER = "what did the ingest job do last night?"

SCHEDULE = "0 8 * * 1-5"
BRIEFING = "Weekday briefing"
BRIEFING_ASK = "Summarise anything that needs my attention this morning."


def _say(what: str, how: str) -> None:
    """Print what was done to one seeded thing."""
    print(f"  {how:<8} {what}")


async def _space() -> str:
    """Make sure the seeded space exists, and return its id."""
    from agent.src.spaces import store, timeline

    for found in await store.all_spaces():
        if found.name == SPACE:
            _say(f"space {SPACE!r}", "kept")
            space_id = found.space_id
            break
    else:
        made = await store.create(name=SPACE, group_cn=GROUP, created_by=WHO)
        _say(f"space {SPACE!r}", "made")
        space_id = made.space_id

    page = await timeline.read(space_id, caller=WHO, after_seq=0, limit=200)
    if page["messages"]:
        _say(f"{len(page['messages'])} message(s) in it", "kept")
    else:
        for text in MESSAGES:
            await timeline.post(space_id, author=WHO, body=text)
        _say(f"{len(MESSAGES)} message(s) in it", "made")
    return space_id


async def _profile() -> None:
    """Make sure the seeded user has a profile."""
    from agent.src.users.store import load_profile, save_profile

    if (await load_profile(WHO)).get("display_name"):
        _say(f"profile for {WHO}", "kept")
        return
    await save_profile(
        WHO,
        {"display_name": "Dev User", "title": "Platform engineer", "timezone": "UTC"},
        updated_by="seed",
    )
    _say(f"profile for {WHO}", "made")


async def _mcp_token() -> None:
    """So a restart does not cost an OAuth dance."""
    from agent.aegra.mcp_token_store import McpTokenStore
    from agent.src.settings import settings

    store = McpTokenStore(settings.database_uri)
    await store.ensure_tables()
    if await store.get_token("agent", WHO, MCP):
        _say(f"mcp token for {MCP}", "kept")
        return
    await store.upsert_token("agent", WHO, MCP, access_token="seeded-not-a-secret")
    _say(f"mcp token for {MCP}", "made")


def _headers() -> dict[str, str]:
    """The headers every request to the agent carries."""
    headers = {"Content-Type": "application/json"}
    if AGENT_HOST:
        headers["Host"] = AGENT_HOST
    return headers


def _post(path: str, body: dict, timeout: int = 30) -> dict:
    """POST `body` to `path` on the agent and return the decoded reply."""
    import json
    import urllib.request

    request = urllib.request.Request(
        f"{AGENT}{path}",
        method="POST",
        data=json.dumps(body).encode(),
        headers=_headers(),
    )
    with urllib.request.urlopen(request, timeout=timeout) as answer:
        parsed: dict = json.load(answer)
    return parsed


def _get(path: str, timeout: int = 30) -> dict:
    """GET `path` on the agent and return the decoded reply."""
    import json
    import urllib.request

    request = urllib.request.Request(f"{AGENT}{path}", headers=_headers())
    with urllib.request.urlopen(request, timeout=timeout) as answer:
        parsed: dict = json.load(answer)
    return parsed


def _on_the_mock() -> bool:
    """Whether a run here is free."""
    try:
        found = _get("/config/settings")
    except Exception:  # noqa: BLE001
        return False
    for field in found.get("fields") or []:
        if field.get("name") == "MODEL_OVERRIDE":
            return str(field.get("value") or "").startswith("mock")
    return False


def _thread() -> None:
    """Make sure the seeded thread exists."""
    existing = _get("/threads")
    for thread in existing.get("threads", []):
        if (thread.get("metadata") or {}).get("thread_name") == THREAD:
            _say(f"thread {THREAD!r}", "kept")
            return

    made = _post("/threads", {"metadata": {"thread_name": THREAD, "seeded": True}})
    thread_id = made["thread_id"]
    _say(f"thread {THREAD!r}", "made")

    if not _on_the_mock():
        _say(
            "conversation: the agent is on a real provider, and seeding "
            "should not spend money (make dev MODEL=mock)",
            "skipped",
        )
        return

    _post(
        f"/threads/{thread_id}/runs/wait",
        {
            "assistant_id": "agent",
            "input": {"messages": [{"role": "human", "content": OPENER}]},
        },
        timeout=120,
    )
    _say("a turn in it, answered by the mock model", "made")


def _schedule() -> None:
    """Make sure the seeded schedule exists."""
    found: Any = _post("/runs/crons/search", {"limit": 50})
    crons = found if isinstance(found, list) else found.get("crons", [])
    for cron in crons:
        if (cron.get("metadata") or {}).get("seeded_name") == BRIEFING:
            _say(f"schedule {BRIEFING!r}", "kept")
            return

    thread_id = _post(
        "/threads",
        {"metadata": {"thread_name": BRIEFING, "seeded": True}},
    )["thread_id"]
    _post(
        f"/threads/{thread_id}/runs/crons",
        {
            "assistant_id": "agent",
            "schedule": SCHEDULE,
            "input": {"messages": [{"role": "human", "content": BRIEFING_ASK}]},
            "metadata": {"seeded": True, "seeded_name": BRIEFING},
            "on_run_completed": "keep",
        },
    )
    _say(f"schedule {BRIEFING!r} ({SCHEDULE})", "made")


async def main() -> int:
    """Seed the local deployment with a space, profile, thread and schedule."""
    print("── seeding")
    await _space()
    await _profile()
    await _mcp_token()
    try:
        _thread()
    except Exception as error:  # noqa: BLE001
        _say(f"thread: {error}", "skipped")
    try:
        _schedule()
    except Exception as error:  # noqa: BLE001
        _say(f"schedule: {error}", "skipped")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
