"""Drive the /spaces routes against the running cluster."""

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

ROOM = "strand-c-probe"
GROUP = "probe-group"

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
        print(f"  {name:<38} round-trips")
        return
    failures.append(name)
    print(f"  {name:<38} DOES NOT round-trip", file=sys.stderr)
    print(f"    sent     {json.dumps(body)[:300]}", file=sys.stderr)
    print(f"    declared {json.dumps(dumped)[:300]}", file=sys.stderr)


def the_room() -> str:
    """Probe space creation and listing, and return a space id."""
    from agent.aegra.space_routes import SpaceListOut, SpaceOut

    code, listed, _ = call("GET", "/spaces")
    if code != 200:
        raise SystemExit(f"/spaces: {code} {listed}")
    roundtrips("GET  /spaces", SpaceListOut, listed)

    for one in listed["spaces"]:
        if one["name"] == ROOM:
            print(f"  reusing the room from a previous run: {one['space_id']}")
            found: str = one["space_id"]
            return found

    code, made, _ = call("POST", "/spaces", {"name": ROOM, "group_cn": GROUP})
    if code != 200:
        raise SystemExit(f"could not open a room: {code} {made}")
    roundtrips("POST /spaces", SpaceOut, made)
    print(f"  opened {made['space_id']}; there is no delete, so it stays")
    made_id: str = made["space_id"]
    return made_id


def reading(space_id: str) -> None:
    """Probe the read-only views of a space."""
    from agent.aegra.space_routes import (
        ActiveRunOut,
        PeopleOut,
        SpaceOut,
        SpendOut,
    )

    code, one, _ = call("GET", f"/spaces/{space_id}")
    if code != 200:
        raise SystemExit(f"cannot read the room: {code} {one}")
    roundtrips("GET  /spaces/{id}", SpaceOut, one)

    code, people, _ = call("GET", f"/spaces/{space_id}/people")
    roundtrips("GET  /spaces/{id}/people", PeopleOut, people)

    code, running, _ = call("GET", f"/spaces/{space_id}/run")
    roundtrips("GET  /spaces/{id}/run", ActiveRunOut, running)

    code, spend, _ = call("GET", f"/spaces/{space_id}/spend")
    if code != 200:
        raise SystemExit(f"/spend: {code} {spend}")
    if not spend["rows"]:
        print("  spend has no billed runs here; shape checked on an empty month")
    roundtrips("GET  /spaces/{id}/spend", SpendOut, spend)


def talking(space_id: str) -> None:
    """Probe posting, pinning and reacting in a space."""
    from agent.aegra.space_routes import (
        AddressedOut,
        MessageOut,
        PinsOut,
        ReactionAddedOut,
        ReactionRemovedOut,
        TimelineOut,
    )

    print("/spaces, writing")
    code, posted, _ = call(
        "POST", f"/spaces/{space_id}/messages", {"body": "a message from the probe"}
    )
    if code != 200:
        raise SystemExit(f"could not post: {code} {posted}")
    roundtrips("POST /spaces/{id}/messages", MessageOut, posted)
    message_id = posted["id"]

    code, page, _ = call("GET", f"/spaces/{space_id}/messages")
    if message_id not in [one["id"] for one in page["messages"]]:
        raise SystemExit("the message was accepted and is not in the room")
    print(f"  the room now has {len(page['messages'])} message(s)")
    roundtrips("GET  /spaces/{id}/messages", TimelineOut, page)

    code, resumed, _ = call(
        "GET",
        f"/spaces/{space_id}/messages?after_seq={page['next_seq']}",
    )
    if resumed["messages"]:
        raise SystemExit("resuming from the last sequence returned messages again")
    roundtrips("GET  /spaces/{id}/messages?after_seq", TimelineOut, resumed)

    code, reacted, _ = call(
        "POST", f"/spaces/{space_id}/messages/{message_id}/reactions", {"emoji": "👀"}
    )
    roundtrips("POST …/reactions", ReactionAddedOut, reacted)

    code, unreacted, _ = call(
        "DELETE", f"/spaces/{space_id}/messages/{message_id}/reactions/%F0%9F%91%80"
    )
    roundtrips("DEL  …/reactions/{emoji}", ReactionRemovedOut, unreacted)

    code, pinned, _ = call(
        "POST", f"/spaces/{space_id}/messages/{message_id}/pin", {"pinned": True}
    )
    roundtrips("POST …/pin", MessageOut, pinned)
    if not pinned["pinned"]:
        raise SystemExit("the message was pinned and does not say so")

    code, pins, _ = call("GET", f"/spaces/{space_id}/pins")
    if message_id not in [one["id"] for one in pins["pins"]]:
        raise SystemExit("the message was pinned and is not in the pins")
    roundtrips("GET  /spaces/{id}/pins", PinsOut, pins)

    call("POST", f"/spaces/{space_id}/messages/{message_id}/pin", {"pinned": False})

    code, verdict, _ = call(
        "POST", f"/spaces/{space_id}/addressed", {"text": "hello, are you there?"}
    )
    roundtrips("POST /spaces/{id}/addressed", AddressedOut, verdict)


def the_run_slot(space_id: str) -> None:
    """Probe claiming, approving and releasing a space's run slot."""
    from agent.aegra.space_routes import (
        ActiveRunOut,
        AlwaysOnOut,
        ApprovedOut,
        RunReleasedOut,
    )

    print("/spaces, the run slot and always-on")
    code, claimed, _ = call(
        "POST", f"/spaces/{space_id}/run", {"run_id": "strand-c-probe-run"}
    )
    if code != 200:
        raise SystemExit(f"could not claim the run slot: {code} {claimed}")
    roundtrips("POST /spaces/{id}/run", ActiveRunOut, claimed)

    code, running, _ = call("GET", f"/spaces/{space_id}/run")
    if running["run_id"] != "strand-c-probe-run":
        raise SystemExit("the slot was claimed and the room does not show it")

    code, approved, _ = call("POST", f"/spaces/{space_id}/approve")
    if code == 200:
        roundtrips("POST /spaces/{id}/approve", ApprovedOut, approved)
    else:
        print(f"  approve answered {code}; not the probe's run to answer")

    code, released, _ = call("DELETE", f"/spaces/{space_id}/run/strand-c-probe-run")
    roundtrips("DEL  /spaces/{id}/run/{run_id}", RunReleasedOut, released)
    code, running, _ = call("GET", f"/spaces/{space_id}/run")
    if running["run_id"] is not None:
        raise SystemExit("the slot was released and is still held")

    code, toggled, _ = call("PATCH", f"/spaces/{space_id}", {"always_on": True})
    roundtrips("PATCH /spaces/{id}", AlwaysOnOut, toggled)
    code, one, _ = call("GET", f"/spaces/{space_id}")
    if not one["always_on"]:
        raise SystemExit(
            "always_on was set and the room does not read it back — this is the "
            "field `response_model=` was dropping"
        )
    print("  always-on set, and the room reads it back")
    call("PATCH", f"/spaces/{space_id}", {"always_on": False})


def the_stream(space_id: str) -> None:
    """Not a document: check the media type, not a model."""
    request = urllib.request.Request(f"{BASE}/spaces/{space_id}/stream")
    request.add_header("Host", HOST)
    with urllib.request.urlopen(request, timeout=10) as answer:
        kind = answer.headers.get("content-type", "")
        first = answer.readline().decode()
    if not kind.startswith("text/event-stream"):
        failures.append("/spaces/{id}/stream")
        print(f"  the stream sends {kind}, and the contract says SSE", file=sys.stderr)
        return
    print(f"  the stream sends {kind} and opens with {first.strip()!r}")


def main() -> int:
    """Run every space probe in order."""
    print("/spaces")
    space_id = the_room()
    reading(space_id)
    talking(space_id)
    the_run_slot(space_id)
    the_stream(space_id)

    if failures:
        print(
            f"\n{len(failures)} response(s) do not match the declared shape",
            file=sys.stderr,
        )
        return 1
    print("\nevery response checked matches the shape its route declares")
    print("the room and its messages stay: /spaces and the timeline have no delete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
