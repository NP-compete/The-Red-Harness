"""Audit event type constants."""

from typing import Final

LLM_CALL: Final = "llm_call"
MCP_TOOL_CALL: Final = "mcp_tool_call"
MEMORY_WRITE: Final = "memory_write"
SUBAGENT_DELEGATION: Final = "subagent_delegation"
CAPABILITY_IMPLICIT_GRANT: Final = "capability_implicit_grant"
CAPABILITY_DENIED: Final = "capability_denied"

DATA_UPLOAD: Final = "data_upload"
DATA_DELETE: Final = "data_delete"
DATA_UPLOAD_REJECTED: Final = "data_upload_rejected"

SECRET_RESOLVED: Final = "secret_resolved"

CONFIG_EDITED: Final = "config_edited"
CONFIG_EDIT_REFUSED: Final = "config_edit_refused"

USER_MUTATION: Final = "user_mutation"
USER_MUTATION_REFUSED: Final = "user_mutation_refused"

APPROVAL_DECIDED: Final = "approval_decided"
PROPOSAL_WEIGHED: Final = "proposal_weighed"
PROPOSAL_REFUSED: Final = "proposal_refused"

AUDITED_MIDDLEWARE_EVENTS: frozenset[str] = frozenset(
    {LLM_CALL, MCP_TOOL_CALL, MEMORY_WRITE, SUBAGENT_DELEGATION}
)


class AuditEventType:
    """Namespace for platform audit event type strings."""

    LLM_CALL = LLM_CALL
    MCP_TOOL_CALL = MCP_TOOL_CALL
    MEMORY_WRITE = MEMORY_WRITE
    SUBAGENT_DELEGATION = SUBAGENT_DELEGATION
    CAPABILITY_IMPLICIT_GRANT = CAPABILITY_IMPLICIT_GRANT
    CAPABILITY_DENIED = CAPABILITY_DENIED
    DATA_UPLOAD = DATA_UPLOAD
    DATA_DELETE = DATA_DELETE
    DATA_UPLOAD_REJECTED = DATA_UPLOAD_REJECTED
    SECRET_RESOLVED = SECRET_RESOLVED
    CONFIG_EDITED = CONFIG_EDITED
    CONFIG_EDIT_REFUSED = CONFIG_EDIT_REFUSED
    USER_MUTATION = USER_MUTATION
    USER_MUTATION_REFUSED = USER_MUTATION_REFUSED
    APPROVAL_DECIDED = APPROVAL_DECIDED
    PROPOSAL_WEIGHED = PROPOSAL_WEIGHED
    PROPOSAL_REFUSED = PROPOSAL_REFUSED
