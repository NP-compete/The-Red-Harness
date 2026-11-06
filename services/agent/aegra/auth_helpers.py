"""Shared authentication helpers for Aegra route handlers."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException, Request

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


async def check_ldap_role(request: Request, *, developer_only: bool = False) -> str:
    """Extract user ID from JWT and resolve LDAP role."""
    from agent.aegra.auth import ENABLE_AUTH, _decode_token

    if not ENABLE_AUTH:
        from agent.aegra.auth import DEV_USER_ID

        return DEV_USER_ID

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    import jwt

    try:
        payload = await asyncio.to_thread(_decode_token, auth_header[7:])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired") from None
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from None
    user_id = str(payload.get("preferred_username") or payload.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identity")

    from agent.src.ldap import PRIVILEGED_ROLES, resolve_user_role

    role = await resolve_user_role(user_id)

    if role == "denied":
        raise HTTPException(
            status_code=403,
            detail="Access denied: not a member of any configured LDAP group",
        )

    if developer_only and role is not None and role not in PRIVILEGED_ROLES:
        raise HTTPException(status_code=403, detail="Developer access required")

    return user_id


async def authenticated_user_id(
    request: Request,
    *,
    reject_anonymous: bool = False,
    developer_only: bool = False,
) -> str:
    """Extract and return the authenticated user's identity from the JWT."""
    from agent.aegra.auth import DEV_USER_ID, ENABLE_AUTH, _decode_token

    if not ENABLE_AUTH:
        return DEV_USER_ID

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        if reject_anonymous:
            raise HTTPException(
                status_code=401, detail="Missing or invalid Authorization header"
            )
        return "anonymous"

    payload = await asyncio.to_thread(_decode_token, auth_header[7:])

    if developer_only:
        user_id = str(
            payload.get("preferred_username") or payload.get("sub") or ""
        ).strip()
        from agent.src.ldap import PRIVILEGED_ROLES, resolve_user_role

        role = await resolve_user_role(user_id)
        if role is not None and role not in PRIVILEGED_ROLES:
            raise HTTPException(status_code=403, detail="Developer access required")

    return str(payload["sub"])


async def role_identity(request: Request) -> str:
    """The identity LDAP knows this caller by."""
    from agent.aegra.auth import _decode_token

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return ""
    payload = await asyncio.to_thread(_decode_token, auth_header[7:])
    return str(payload.get("preferred_username") or payload.get("sub") or "").strip()


async def memory_user_id(request: Request) -> str:
    """User id for LangGraph Store memories (preferred_username / X-User-ID)."""
    from agent.aegra.auth import DEV_USER_ID, ENABLE_AUTH, _decode_token

    header = (request.headers.get("x-user-id") or "").strip()

    if not ENABLE_AUTH:
        return header or DEV_USER_ID

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    payload = await asyncio.to_thread(_decode_token, auth_header[7:])
    token_uid = str(
        payload.get("preferred_username") or payload.get("sub") or ""
    ).strip()
    if not token_uid:
        raise HTTPException(
            status_code=401, detail="Token missing preferred_username and sub"
        )

    if header and header != token_uid:
        raise HTTPException(
            status_code=403, detail="X-User-ID does not match authenticated user"
        )

    return token_uid


async def rule_user_ids(request: Request) -> list[str]:
    """Owner key for Custom Rules — same id as memories and the chat graph."""
    return [await memory_user_id(request)]
