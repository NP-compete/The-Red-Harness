"""LDAP-based access control for the template agent."""

from agent.src.ldap.prompt_config import (
    PRIVILEGED_ROLES,
    ROLE_HIERARCHY,
    get_prompt_access_config,
)
from agent.src.ldap.service import (
    close_ldap,
    resolve_user_groups,
    resolve_user_role,
)

__all__ = [
    "PRIVILEGED_ROLES",
    "ROLE_HIERARCHY",
    "close_ldap",
    "get_prompt_access_config",
    "resolve_user_groups",
    "resolve_user_role",
]
