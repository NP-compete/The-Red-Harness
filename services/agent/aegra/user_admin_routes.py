"""Administrator reads and writes against a person's profile (E9-T2)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.aegra.auth_helpers import check_ldap_role
from agent.src.audit.events import AuditEventType
from agent.src.users.authorization import decide, decide_all
from agent.src.users.profiles import PROFILE_FIELDS, ProfileError, validate
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/admin/users", tags=["user-admin"])

FIELD_CLASSES = ("profile", "membership", "entitlement")


class ProfilePatch(BaseModel):
    """Request body changing fields on a user's profile."""

    fields: dict[str, Any]


class PermissionOut(BaseModel):
    """Whether the caller may write one class of profile field."""

    field_class: str
    allowed: bool
    reasons: list[str]
    writable_here: bool


class PermissionsOut(BaseModel):
    """What the caller may change on a user's profile."""

    user_id: str
    actor_role: str
    target_role: str
    classes: list[PermissionOut]


def _record(event_type: str, **details: Any) -> None:
    """Note it for the trail, never at the cost of the answer."""
    from agent.src.audit import emit_audit_event

    try:
        emit_audit_event(event_type, **details)
    except Exception:  # noqa: BLE001
        logger.debug("Could not record a user-administration event", exc_info=True)


DEV_ROLE = "owners"


async def _role_of(user_id: str) -> str:
    """The target's role, as the identity provider reports it."""
    from agent.aegra.auth import ENABLE_AUTH
    from agent.src.ldap.service import resolve_user_role

    if not ENABLE_AUTH:
        return DEV_ROLE

    try:
        return await resolve_user_role(user_id) or "users"
    except Exception:  # noqa: BLE001
        return "unknown"


@router.get("/{user_id}/permissions", response_model=PermissionsOut)
async def permissions(request: Request, user_id: str) -> dict[str, Any]:
    """What the policy would allow, per class, for this actor."""
    actor = await check_ldap_role(request, developer_only=True)
    actor_role = await _role_of(actor)
    target_role = await _role_of(user_id)

    decisions = await decide_all(
        actor_role=actor_role,
        target_role=target_role,
        field_classes=list(FIELD_CLASSES),
    )
    return {
        "user_id": user_id,
        "actor_role": actor_role,
        "target_role": target_role,
        "classes": [
            {
                "field_class": d.field_class,
                "allowed": d.allowed,
                "reasons": d.reasons,
                "writable_here": d.field_class == "profile",
            }
            for d in decisions
        ],
    }


class ProfileOut(BaseModel):
    """A user's profile and who last changed it."""

    user_id: str
    fields: dict[str, Any] = {}
    updated_by: str | None = None
    updated_at: str | None = None
    writable_fields: list[str] | None = None


class DeparturePlanOut(BaseModel):
    """What leaving would do, or has done."""

    subject: str
    revoke_connections: list[str] = []
    stop_agents: list[str] = []
    reason: str = ""
    team_content: str = ""
    delegations: str = ""
    done: list[str] | None = None
    failed: list[str] | None = None
    personal_content_erased: Any = None


@router.patch(
    "/{user_id}/profile", response_model=None, responses={200: {"model": ProfileOut}}
)
async def patch_profile(
    request: Request, user_id: str, body: ProfilePatch
) -> dict[str, Any] | JSONResponse:
    """Correct a person's profile, if the policy allows it."""
    actor = await check_ldap_role(request, developer_only=True)

    try:
        changes = validate(body.fields)
    except ProfileError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": "bad_request", "message": str(exc)},
        )

    actor_role = await _role_of(actor)
    target_role = await _role_of(user_id)
    verdict = await decide(
        actor_role=actor_role, target_role=target_role, field_class="profile"
    )

    if not verdict.allowed:
        _record(
            AuditEventType.USER_MUTATION_REFUSED,
            actor=actor,
            actor_role=actor_role,
            target=user_id,
            target_role=target_role,
            field_class="profile",
            fields=sorted(changes),
            reason=verdict.why,
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": "forbidden",
                "message": verdict.why,
                "field_class": "profile",
            },
        )

    from agent.src.users.store import save_profile

    saved = await save_profile(user_id, changes, updated_by=actor)
    _record(
        AuditEventType.USER_MUTATION,
        actor=actor,
        actor_role=actor_role,
        target=user_id,
        target_role=target_role,
        field_class="profile",
        fields=sorted(changes),
        decision="allowed",
    )
    logger.warning(
        "Profile changed: %s by %s (%s)", user_id, actor, ", ".join(sorted(changes))
    )
    return saved


@router.get(
    "/{user_id}/profile", response_model=None, responses={200: {"model": ProfileOut}}
)
async def read_profile(request: Request, user_id: str) -> dict[str, Any]:
    """The profile overrides held for this person, if any."""
    await check_ldap_role(request, developer_only=True)
    from agent.src.users.store import load_profile

    return {
        "user_id": user_id,
        "fields": await load_profile(user_id),
        "writable_fields": list(PROFILE_FIELDS),
    }


def _configured_servers() -> tuple[str, ...]:
    """Every MCP server this deployment knows about."""
    try:
        from agent.src.agent.config import agent_config

        return tuple(sorted(agent_config.get_mcp_servers() or {}))
    except Exception:  # noqa: BLE001
        logger.debug("Could not list MCP servers for a departure", exc_info=True)
        return ()


def _plan_for(user_id: str) -> Any:
    """The departure plan for `user_id`."""
    from agent.src.security.departure import plan_departure

    return plan_departure(
        subject=user_id,
        collections=[],
        connected_servers=list(_configured_servers()),
        granted_delegations=[],
    )


def _as_payload(plan: Any) -> dict[str, Any]:
    """A departure plan as a response body."""
    return {
        "subject": plan.subject,
        "revoke_connections": list(plan.revoke_connections),
        "stop_agents": list(plan.stop_agents),
        "reason": plan.reason,
        "team_content": "left in place; it was never theirs alone",
        "delegations": (
            "none recorded — this deployment keeps no grant store yet, "
            "so an unattended run started on this person's authority "
            "would not appear here"
        ),
    }


@router.get(
    "/{user_id}/departure",
    response_model=None,
    responses={200: {"model": DeparturePlanOut}},
)
async def preview_departure(request: Request, user_id: str) -> dict[str, Any]:
    """What leaving would do to this person's access. Changes nothing."""
    await check_ldap_role(request, developer_only=True)
    from agent.aegra.my_data_routes import _held_about

    payload = _as_payload(_plan_for(user_id))
    held = _held_about(user_id)
    payload["personal_content"] = {section: len(rows) for section, rows in held.items()}
    return payload


class DepartureAsked(BaseModel):
    """Request body starting a user's departure."""

    erase_personal: bool = False


@router.post(
    "/{user_id}/departure",
    response_model=None,
    responses={200: {"model": DeparturePlanOut}},
)
async def carry_out_departure(
    request: Request, user_id: str, body: DepartureAsked
) -> dict[str, Any] | JSONResponse:
    """Revoke this person's access, and report what did not happen."""
    actor = await check_ldap_role(request, developer_only=True)
    actor_role = await _role_of(actor)
    target_role = await _role_of(user_id)

    verdict = await decide(
        actor_role=actor_role, target_role=target_role, field_class="entitlement"
    )
    if not verdict.allowed:
        _record(
            AuditEventType.USER_MUTATION,
            actor=actor,
            actor_role=actor_role,
            target=user_id,
            target_role=target_role,
            field_class="entitlement",
            decision="refused",
            reasons=verdict.reasons,
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": "forbidden",
                "message": verdict.why,
                "field_class": "entitlement",
            },
        )

    from agent.src.security.departure import LiveDeparture, carry_out

    plan = _plan_for(user_id)
    outcome = await carry_out(plan, doer=LiveDeparture())

    erased: dict[str, Any] = {}
    if body.erase_personal:
        from agent.aegra.my_data_routes import _collect_async, _remove_async

        held = await _collect_async(user_id)
        for section, rows in held.items():
            ids = [str(row.get("id")) for row in rows if row.get("id")]
            if not ids:
                continue
            try:
                await _remove_async(user_id, section, ids)
                erased[section] = len(ids)
            except Exception as error:  # noqa: BLE001
                outcome.failed.append(f"erase {section}: {error}")

    _record(
        AuditEventType.USER_MUTATION,
        actor=actor,
        actor_role=actor_role,
        target=user_id,
        target_role=target_role,
        field_class="entitlement",
        decision="allowed",
        done=outcome.done,
        failed=outcome.failed,
    )
    logger.warning(
        "Departure carried out for %s by %s: %d done, %d failed",
        user_id,
        actor,
        len(outcome.done),
        len(outcome.failed),
    )

    payload = _as_payload(plan)
    payload.update(
        {
            "done": outcome.done,
            "failed": outcome.failed,
            "personal_content_erased": erased or "not asked for",
        }
    )
    return payload
