"""The small route groups, against the running cluster."""

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

UNVERIFIED = {
    "POST /features/{key}": "flips a deployment-wide switch",
    "POST /channels/{name}": "needs a signed provider delivery",
    "POST /speech/transcribe": "needs audio and a transcriber",
    "POST /search/reindex": "and GET /search/threads need an index",
    "DELETE /me/data": "deletes everything the caller owns",
    "GET/POST /admin/users/{id}/departure": "revokes real credentials",
    "PATCH /admin/users/{id}/profile": "writes to a real person's profile",
    "GET /.well-known/agent-card.json": "404 unless the inbound door is open",
    "GET /analytics/users": "404 unless analytics.expose_users is on",
    "GET /tags/{tag}/threads": "needs a tagged thread, which needs messages",
    "POST /a2a": "needs the inbound door open and an identified peer",
    "POST /answers/notes": "needs an answer to annotate",
    "POST /projects/assign": "needs a thread and a project",
    "POST /feedback": "writes a rating against a real conversation",
    "GET /shared/{share_id}": "needs a share, which needs messages",
    "GET /v1/eval/*": "the eval harness drives these, not a browser",
}

failures: list[str] = []


def fetch(route: str) -> tuple[int, Any, str]:
    """GET a route and return the status, decoded body and content type."""
    request = urllib.request.Request(BASE + route)
    request.add_header("Host", HOST)
    try:
        with urllib.request.urlopen(request, timeout=60) as answer:
            raw, kind = answer.read(), answer.headers.get("content-type", "")
            code = answer.status
    except urllib.error.HTTPError as failed:
        raw, kind, code = (
            failed.read(),
            failed.headers.get("content-type", ""),
            failed.code,
        )
    body: object = raw
    if raw and kind.startswith("application/json"):
        body = json.loads(raw)
    return code, body, kind


def roundtrips(route: str, model: type[BaseModel], body: Any) -> None:
    """Report whether `body` survives a round trip through `model`."""
    dumped = model.model_validate(body).model_dump(
        mode="json", by_alias=True, exclude_unset=True
    )
    if dumped == body:
        print(f"  {route:<34} round-trips")
        return
    failures.append(route)
    print(f"  {route:<34} DOES NOT round-trip", file=sys.stderr)
    print(f"    sent     {json.dumps(body)[:300]}", file=sys.stderr)
    print(f"    declared {json.dumps(dumped)[:300]}", file=sys.stderr)


def main() -> int:
    """Probe the routes that are too small to warrant their own script."""
    from agent.aegra.app_models import HealthProbeOut
    from agent.aegra.attachment_routes import ExtractionStatusOut
    from agent.aegra.channel_routes import ChannelListOut
    from agent.aegra.command_routes import CommandsOut
    from agent.aegra.costs_routes import ChargebackOut
    from agent.aegra.extension_routes import ExtensionsOut
    from agent.aegra.feature_routes import FeaturesOut
    from agent.aegra.limits_routes import MyLimitsOut
    from agent.aegra.mcp_routes import OAuthClientOut
    from agent.aegra.my_data_routes import DeletionPreviewOut, MyDataExportOut
    from agent.aegra.rates_routes import PriceOut, RateCardOut
    from agent.aegra.reasoning_routes import ReasoningProfilesOut
    from agent.aegra.share_routes import MySharesOut
    from agent.aegra.skill_routes import (
        ConfiguredModelsOut,
        PermissionsOut,
        SafeguardsOut,
        SkillFilesOut,
        SkillsOut,
        SubagentsOut,
        WhoamiOut,
    )
    from agent.aegra.speech_routes import DictationOut
    from agent.aegra.tag_routes import TagListOut
    from agent.aegra.workspace_routes import WorkspaceFilesOut

    print("the small groups, read")
    for route, model in (
        ("/features", FeaturesOut),
        ("/rates", RateCardOut),
        ("/rates/price", PriceOut),
        ("/skills", SkillsOut),
        ("/subagents", SubagentsOut),
        ("/tags", TagListOut),
        ("/speech", DictationOut),
        ("/channels/", ChannelListOut),
        ("/workspace/files", WorkspaceFilesOut),
        ("/me/export", MyDataExportOut),
        ("/me/deletion-preview", DeletionPreviewOut),
        ("/.well-known/oauth-client", OAuthClientOut),
        ("/commands", CommandsOut),
        ("/extensions", ExtensionsOut),
        ("/models", ConfiguredModelsOut),
        ("/permissions", PermissionsOut),
        ("/prompt", SkillFilesOut),
        ("/safeguards", SafeguardsOut),
        ("/auth/whoami", WhoamiOut),
        ("/reasoning-profiles", ReasoningProfilesOut),
        ("/limits/mine", MyLimitsOut),
        ("/costs/chargeback", ChargebackOut),
        ("/shares", MySharesOut),
        ("/attachments/extraction", ExtractionStatusOut),
        ("/healthz", HealthProbeOut),
        ("/livez", HealthProbeOut),
        ("/readyz", HealthProbeOut),
    ):
        code, body, _ = fetch(route)
        if code != 200:
            raise SystemExit(f"{route}: {code} {body}")
        roundtrips(f"GET  {route}", model, body)

    code, skills, _ = fetch("/skills")
    if skills["skills"]:
        name = skills["skills"][0]["name"]
        code, one, _ = fetch(f"/skills/{name}")
        roundtrips(f"GET  /skills/{name}", SkillFilesOut, one)
    else:
        print("  no skills configured; /skills/{name} unchecked")

    code, subagents, _ = fetch("/subagents")
    if subagents["subagents"]:
        name = subagents["subagents"][0]["name"]
        code, one, _ = fetch(f"/subagents/{name}")
        roundtrips(f"GET  /subagents/{name}", SkillFilesOut, one)
    else:
        print("  no subagents configured; /subagents/{name} unchecked")

    code, _body, kind = fetch("/analytics/export?what=models&days=7")
    if code != 200 or not kind.startswith("text/csv"):
        failures.append("/analytics/export")
        print(f"  /analytics/export answered {code} {kind}, want CSV", file=sys.stderr)
    else:
        print(f"  /analytics/export sends {kind}, as declared")

    if failures:
        print(
            f"\n{len(failures)} response(s) do not match the declared shape",
            file=sys.stderr,
        )
        return 1
    print("\nevery response checked matches the shape its route declares")
    print("\ndeclared from the handlers, not safe or possible to drive here:")
    for route, why in UNVERIFIED.items():
        print(f"  {route:<40} {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
