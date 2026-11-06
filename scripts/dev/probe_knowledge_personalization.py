"""Drive /knowledge and /personalization against the running cluster."""

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

failures: list[str] = []


def call(method: str, route: str, body: dict | None = None) -> tuple[int, Any]:
    """Call the agent and return the status and decoded body."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + route, data=data, method=method)
    request.add_header("Host", HOST)
    if data:
        request.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as answer:
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
        print(f"  {name:<34} round-trips")
        return
    failures.append(name)
    print(f"  {name:<34} DOES NOT round-trip", file=sys.stderr)
    print(f"    sent     {json.dumps(body)[:300]}", file=sys.stderr)
    print(f"    declared {json.dumps(dumped)[:300]}", file=sys.stderr)


AGENT_YAML = "config/agent/runtime/agent.yaml"


def turn_knowledge_on() -> bool:
    """Enable the personal corpus the way a deployment would."""
    if call("GET", "/knowledge/documents")[0] == 200:
        return False

    code, current = call("GET", f"/config/file?path={AGENT_YAML}")
    if code != 200:
        raise SystemExit(f"cannot read {AGENT_YAML}: {code} {current}")
    text = current["text" if "text" in current else "content"]
    changed = text.replace(
        "knowledge:\n  enabled: false", "knowledge:\n  enabled: true", 1
    )
    if changed == text:
        raise SystemExit("could not find `knowledge.enabled` in the agent file")

    code, written = call(
        "PUT",
        "/config/edit",
        {
            "path": AGENT_YAML,
            "content": changed,
            "base_version": current["version"],
        },
    )
    if code != 200:
        raise SystemExit(f"could not enable the corpus: {code} {written}")

    code = call("GET", "/knowledge/documents")[0]
    if code != 200:
        raise SystemExit(
            "the edit was accepted and the agent still answers "
            f"{code} — the overlay is not reaching the loader"
        )
    print("  turned the corpus on through /config/edit, no restart")
    return True


def turn_knowledge_off() -> None:
    """Drop the override and check the corpus really goes away."""
    code, _ = call("POST", "/config/adopt-baseline", {"path": AGENT_YAML})
    if code != 200:
        raise SystemExit(f"could not drop the override: {code}")
    if call("GET", "/knowledge/documents")[0] == 200:
        raise SystemExit("the override was dropped and the corpus is still on")
    print("  put the corpus back the way the tree has it")


def knowledge() -> None:
    """Probe the knowledge document routes."""
    from agent.aegra.knowledge_routes import (
        KnowledgeAddedOut,
        KnowledgeDocumentTextOut,
        KnowledgeListOut,
        KnowledgeRemovedOut,
        KnowledgeSavedOut,
    )

    code, added = call(
        "POST",
        "/knowledge/documents",
        {"title": "strand-C probe", "text": "a sentence to rewrite."},
    )
    if code != 200:
        raise SystemExit(f"could not add a document: {code} {added}")
    roundtrips("POST /knowledge/documents", KnowledgeAddedOut, added)
    document_id = added["id"]

    code, listed = call("GET", "/knowledge/documents")
    titles = [one["title"] for one in listed["documents"]]
    if "strand-C probe" not in titles:
        raise SystemExit("the document was accepted and is not in the list")
    roundtrips("GET  /knowledge/documents", KnowledgeListOut, listed)

    code, one = call("GET", f"/knowledge/documents/{document_id}")
    if one["text"] != "a sentence to rewrite.":
        raise SystemExit("the agent does not read back the text it stored")
    roundtrips("GET  /knowledge/documents/{id}", KnowledgeDocumentTextOut, one)

    code, saved = call(
        "PUT",
        f"/knowledge/documents/{document_id}",
        {"title": "strand-C probe", "text": "a different sentence."},
    )
    roundtrips("PUT  /knowledge/documents/{id}", KnowledgeSavedOut, saved)

    code, removed = call("DELETE", f"/knowledge/documents/{document_id}")
    roundtrips("DEL  /knowledge/documents/{id}", KnowledgeRemovedOut, removed)

    code, after = call("GET", "/knowledge/documents")
    if any(one["id"] == document_id for one in after["documents"]):
        raise SystemExit("the document is still there after being deleted")
    print("  the document is gone")


def personalization() -> None:
    """Probe the personalization consent and rule routes."""
    from agent.aegra.personalization_routes import (
        ConsentOut,
        DeletedOut,
        RuleListOut,
        RuleOut,
    )

    print("/personalization")
    code, had = call("GET", "/personalization/consent")
    was_granted = bool(had and had["has_consent"])

    code, granted = call("POST", "/personalization/consent")
    if code != 200:
        raise SystemExit(f"consent refused: {code} {granted}")
    roundtrips("POST /personalization/consent", ConsentOut, granted)

    code, rule = call(
        "POST", "/personalization/rules", {"content": "strand-C probe rule"}
    )
    if code != 201:
        raise SystemExit(f"rule refused: {code} {rule}")
    roundtrips("POST /personalization/rules", RuleOut, rule)
    rule_id = rule["id"]

    code, rules = call("GET", "/personalization/rules")
    if rule_id not in [one["id"] for one in rules["rules"]]:
        raise SystemExit("the rule was accepted and is not in the list")
    roundtrips("GET  /personalization/rules", RuleListOut, rules)

    code, deleted = call("DELETE", f"/personalization/rules/{rule_id}")
    roundtrips("DEL  /personalization/rules/{id}", DeletedOut, deleted)

    code, rules = call("GET", "/personalization/rules")
    if rule_id in [one["id"] for one in rules["rules"]]:
        raise SystemExit("the rule is still there after being deleted")
    print("  the rule is gone")

    if not was_granted:
        code, revoked = call("DELETE", "/personalization/consent")
        roundtrips("DEL  /personalization/consent", DeletedOut, revoked)
    else:
        print("  consent was already granted; left as found")


def main() -> int:
    """Run the knowledge and personalization probes."""
    print("/knowledge")
    turned_on = turn_knowledge_on()
    try:
        knowledge()
    finally:
        if turned_on:
            turn_knowledge_off()
    personalization()
    if failures:
        print(
            f"\n{len(failures)} response(s) do not match the declared shape",
            file=sys.stderr,
        )
        return 1
    print("\nevery response matches the shape its route declares")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
