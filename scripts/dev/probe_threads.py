"""Drive the per-thread routes against the running cluster."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services"))

BASE = "http://localhost:8081"
HOST = "agent.localhost"

UPSTREAM = (
    "POST /threads/{id}/commands",
    "POST /threads/{id}/runs/stream",
    "POST /threads/{id}/runs/wait — driven here to seed, shape not ours",
    "GET  /threads/{id}/runs/{run_id}/join",
    "GET  /threads/{id}/runs/{run_id}/stream",
    "DELETE /threads/{id} — the documented operation is aegra's",
)

failures: list[str] = []
unverified: dict[str, str] = {}


def call(
    method: str, route: str, body: dict | None = None, timeout: int = 180
) -> tuple[int, Any]:
    """Call the agent and return the status and decoded body."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + route, data=data, method=method)
    request.add_header("Host", HOST)
    if data:
        request.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            raw = answer.read()
            return answer.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as failed:
        raw = failed.read()
        try:
            return failed.code, (json.loads(raw) if raw else None)
        except json.JSONDecodeError:
            return failed.code, {"body": raw.decode(errors="replace")[:300]}


def upload(route: str, filename: str, content: bytes) -> tuple[int, Any]:
    """`POST .../attachments` is multipart, so it is built by hand."""
    edge = uuid.uuid4().hex
    body = b"".join(
        [
            f"--{edge}\r\n".encode(),
            f'Content-Disposition: form-data; name="files"; '
            f'filename="{filename}"\r\n'.encode(),
            b"Content-Type: text/plain\r\n\r\n",
            content,
            f"\r\n--{edge}--\r\n".encode(),
        ]
    )
    request = urllib.request.Request(BASE + route, data=body, method="POST")
    request.add_header("Host", HOST)
    request.add_header("content-type", f"multipart/form-data; boundary={edge}")
    try:
        with urllib.request.urlopen(request, timeout=120) as answer:
            raw = answer.read()
            return answer.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as failed:
        raw = failed.read()
        return failed.code, (json.loads(raw) if raw else None)


def roundtrips(name: str, model: type[BaseModel], body: Any) -> None:
    """Report whether `body` survives a round trip through `model`."""
    dumped = model.model_validate(body).model_dump(
        mode="json", by_alias=True, exclude_unset=True
    )
    if dumped == body:
        print(f"  {name:<40} round-trips")
        return
    failures.append(name)
    print(f"  {name:<40} DOES NOT round-trip", file=sys.stderr)
    print(f"    sent     {json.dumps(body)[:300]}", file=sys.stderr)
    print(f"    declared {json.dumps(dumped)[:300]}", file=sys.stderr)


def seed(thread_id: str) -> None:
    """Put two messages in the thread, with a real model reply."""
    code, answered = call(
        "POST",
        f"/threads/{thread_id}/runs/wait",
        {
            "assistant_id": "agent",
            "input": {"messages": [{"role": "user", "content": "say pong"}]},
        },
    )
    if code != 200:
        raise SystemExit(
            f"the seeding run failed: {code} {str(answered)[:400]}\n"
            "Every check below needs a conversation with messages in it. If "
            "this is a 500 about building a subagent, look at the permissions "
            "on /app/data before blaming the model credentials."
        )
    said = (answered or {}).get("messages", [])
    if len(said) < 2:
        raise SystemExit(f"the run returned no reply: {said}")
    print(f"  seeded with {len(said)} messages, the last from the model")


def main() -> int:
    """Probe the thread, attachment, fork and handover routes."""
    from agent.aegra.attachment_routes import (
        AttachmentsStoredOut,
        ThreadAttachmentsOut,
    )
    from agent.aegra.fork_routes import ForkedOut
    from agent.aegra.handoff_routes import HandoverOut
    from agent.aegra.share_routes import ShareOut, ThreadShareOut, UnsharedOut
    from agent.aegra.tag_routes import ThreadTagsOut
    from agent.aegra.thread_cleanup import ThreadDeletedOut
    from agent.aegra.truncate_routes import TruncatedOut

    print("/threads")
    code, thread = call("POST", "/threads", {"metadata": {"title": "strand-c probe"}})
    if code not in (200, 201):
        raise SystemExit(f"could not open a thread: {code} {thread}")
    thread_id = thread["thread_id"]
    print(f"  opened {thread_id}")

    forked_id: str | None = None
    try:
        seed(thread_id)

        code, tagged = call(
            "PUT", f"/threads/{thread_id}/tags", {"tags": ["strand-c", "probe"]}
        )
        if code != 200:
            raise SystemExit(f"tagging refused: {code} {tagged}")
        roundtrips("PUT  /threads/{id}/tags", ThreadTagsOut, tagged)

        code, read_back = call("GET", f"/threads/{thread_id}/tags")
        if set(read_back["tags"]) != {"strand-c", "probe"}:
            raise SystemExit(f"the tags do not read back: {read_back}")
        roundtrips("GET  /threads/{id}/tags", ThreadTagsOut, read_back)

        code, share = call("GET", f"/threads/{thread_id}/share")
        if share["shared"]:
            raise SystemExit("a brand-new thread reports itself as shared")
        roundtrips("GET  /threads/{id}/share (unshared)", ThreadShareOut, share)

        code, made = call(
            "POST",
            f"/threads/{thread_id}/share",
            {"scope": "authenticated", "expiry_days": 7},
        )
        if code != 200:
            raise SystemExit(f"sharing refused: {code} {made}")
        if made["messages"] != 2:
            raise SystemExit(
                f"the share counted {made['messages']} messages, not the two "
                "that were seeded — it is sharing something other than this "
                "conversation"
            )
        roundtrips("POST /threads/{id}/share", ShareOut, made)

        code, shared = call("GET", f"/threads/{thread_id}/share")
        if not shared["shared"] or shared["share_id"] != made["share_id"]:
            raise SystemExit(f"the share does not read back: {shared}")
        roundtrips("GET  /threads/{id}/share (shared)", ThreadShareOut, shared)

        code, revoked = call("DELETE", f"/threads/{thread_id}/share")
        if code != 200 or not revoked["revoked"]:
            raise SystemExit(f"the share would not revoke: {code} {revoked}")
        roundtrips("DEL  /threads/{id}/share", UnsharedOut, revoked)

        code, after = call("GET", f"/threads/{thread_id}/share")
        if after["shared"]:
            raise SystemExit("the link was revoked and the thread is still shared")

        code, fork = call(
            "POST",
            f"/threads/{thread_id}/fork",
            {"message_index": 1, "title": "strand-c fork"},
        )
        if code != 200:
            raise SystemExit(f"forking refused: {code} {fork}")
        forked_id = fork["thread_id"]
        if fork["forked_from"] != thread_id or fork["message_count"] != 1:
            raise SystemExit(f"the fork did not cut where it was asked: {fork}")
        roundtrips("POST /threads/{id}/fork", ForkedOut, fork)

        code, handed = call(
            "POST", f"/threads/{thread_id}/handover", {"to": "someone-else"}
        )
        if code != 200:
            raise SystemExit(f"handover refused: {code} {handed}")
        if handed["allowed"] or not handed["waiting"]:
            raise SystemExit(
                f"a handover nobody accepted reports {handed} — it should be "
                "waiting, not allowed"
            )
        roundtrips("POST /threads/{id}/handover", HandoverOut, handed)

        code, stored = upload(
            f"/threads/{thread_id}/attachments", "note.txt", b"hello from the probe"
        )
        if code != 200:
            raise SystemExit(f"the upload was refused: {code} {stored}")
        roundtrips("POST /threads/{id}/attachments", AttachmentsStoredOut, stored)

        code, attachments = call("GET", f"/threads/{thread_id}/attachments")
        if code != 200:
            raise SystemExit(f"/attachments: {code} {attachments}")
        roundtrips("GET  /threads/{id}/attachments", ThreadAttachmentsOut, attachments)

        code, cut = call("POST", f"/threads/{thread_id}/truncate", {"message_index": 1})
        if code != 200:
            raise SystemExit(f"truncation refused: {code} {cut}")
        if cut["removed"] < 1:
            raise SystemExit(
                f"truncation withdrew {cut['removed']} messages from a "
                "two-message conversation cut at index 1"
            )
        roundtrips("POST /threads/{id}/truncate", TruncatedOut, cut)

        code, usage = call("GET", f"/threads/{thread_id}/token-usage")
        if code == 200:
            print("  GET  /threads/{id}/token-usage          answered")
        else:
            unverified["GET /threads/{id}/token-usage"] = (
                f"{code} {(usage or {}).get('message', '')} — the store is "
                "MongoDB and the Kind overlay deploys none"
            )
    finally:
        for one in (forked_id, thread_id):
            if one is None:
                continue
            code, deleted = call("DELETE", f"/threads/{one}")
            if code != 200:
                raise SystemExit(f"could not delete {one}: {code} {deleted}")
            if one == thread_id:
                roundtrips("DEL  /threads/{id}", ThreadDeletedOut, deleted)
        code, gone = call("GET", f"/threads/{thread_id}/tags")
        if code == 200:
            raise SystemExit("the thread was deleted and still answers")
        print("  deleted; nothing left behind")

    if failures:
        print(
            f"\n{len(failures)} response(s) do not match the declared shape",
            file=sys.stderr,
        )
        return 1
    print("\nevery response checked matches the shape its route declares")
    if unverified:
        print("\nnot reachable from this cluster:")
        for route, why in unverified.items():
            print(f"  {route:<40} {why}")
    print("\nupstream in aegra_api, not declared here:")
    for route in UPSTREAM:
        print(f"  {route}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
