"""One object per run: holds the state the five stages share."""

from __future__ import annotations

from agent.src.agent.config.middleware import (
    ApprovalPolicy,
    HumanApprovalConfig,
    MiddlewareDefaults,
    MiddlewareFileConfig,
    ToolCallLimitConfig,
    ToolOutputConfig,
    resolve_middleware,
)
from agent.src.security.guard import build_guard
from agent.src.security.resolver import (
    Allowed,
    Identity,
    NeedsApproval,
    RefusalCode,
    Refused,
    ToolCall,
    Trust,
)
from agent.src.security.trust import ToolResult

SERVERS = {"tracker": {"url": "https://tracker"}, "docs": {"url": "https://docs"}}
SOMEONE = Identity(subject="someone@example.com")
CREATE = ToolCall(name="tracker.create_issue", server="tracker", writes=True)
SEARCH = ToolCall(name="tracker.search", server="tracker")


class Connected:
    async def has_valid_token(self, user_id, mcp_name, server_cfg, *, verify=False):
        return True


def config(**defaults):
    base = {
        "human_approval": HumanApprovalConfig(default_decision="allow"),
        "tool_output": ToolOutputConfig(trusted_servers=["docs"]),
        "tool_call_limit": ToolCallLimitConfig(run_limit=10),
    }
    base.update(defaults)
    return resolve_middleware(
        MiddlewareFileConfig(defaults=MiddlewareDefaults(**base)), "any-model"
    )


def guard(cfg=None, **kwargs):
    return build_guard(
        config=cfg or config(),
        credentials=Connected(),
        servers=SERVERS,
        identity=SOMEONE,
        **kwargs,
    )


def test_a_guard_starts_clean():
    assert guard().context.trust is Trust.CLEAN


def test_it_authorises_a_call():
    assert isinstance(guard().authorise(CREATE), Allowed)


def test_an_untrusted_result_escalates_the_next_write():
    g = guard()
    g.record_result(ToolResult(tool_name="search", server="tracker"))
    assert isinstance(g.authorise(CREATE), NeedsApproval)


def test_a_trusted_result_does_not_escalate():
    g = guard()
    g.record_result(ToolResult(tool_name="list", server="docs"))
    assert isinstance(g.authorise(CREATE), Allowed)


def test_calls_consume_the_run_budget():
    g = guard(config(tool_call_limit=ToolCallLimitConfig(run_limit=1)))
    g.record_call(SEARCH)
    decision = g.authorise(SEARCH)
    assert isinstance(decision, Refused)
    assert decision.code is RefusalCode.BUDGET_EXHAUSTED


def test_the_configured_policy_is_applied():
    cfg = config(
        human_approval=HumanApprovalConfig(
            default_decision="allow",
            policies=[
                ApprovalPolicy(
                    tools=["tracker.create_issue"], decision="deny", reason="no"
                )
            ],
        )
    )
    decision = guard(cfg).authorise(CREATE)
    assert isinstance(decision, Refused)
    assert decision.code is RefusalCode.POLICY_DENIED


def test_every_authorisation_is_journalled():
    g = guard()
    g.authorise(SEARCH)
    g.authorise(CREATE)
    assert [entry.tool for entry in g.journal.entries] == [
        "tracker.search",
        "tracker.create_issue",
    ]


def test_provenance_is_carried_into_the_journal():
    g = guard(fingerprint="cfg_abc", schema_version=3)
    g.authorise(SEARCH)
    entry = g.journal.entries[0]
    assert entry.config_fingerprint == "cfg_abc"
    assert entry.schema_version == 3


def test_a_dry_run_guard_refuses_what_would_have_asked():
    cfg = config(
        human_approval=HumanApprovalConfig(
            default_decision="allow",
            policies=[
                ApprovalPolicy(
                    tools=["tracker.create_issue"], decision="ask", reason="shared"
                )
            ],
        )
    )
    decision = guard(cfg, effects="dry_run").authorise(CREATE)
    assert isinstance(decision, Refused)
    assert decision.code is RefusalCode.POLICY_DENIED
    assert "dry run" in decision.message


def test_token_spend_is_tracked_when_a_limit_is_given():
    g = guard(token_limit=100)
    g.record_tokens(40)
    assert g.spent == (0, 40)


def test_a_delegated_run_without_a_grant_holds_nothing():
    from agent.src.security.resolver import Identity as Id

    g = build_guard(
        config=config(),
        credentials=Connected(),
        servers=SERVERS,
        identity=Id(subject="ticket-triage", delegated_by="someone@example.com"),
    )
    decision = g.authorise(CREATE)
    assert isinstance(decision, Refused)
    assert decision.code is RefusalCode.NO_AUTHORITY


def test_a_delegated_run_within_its_grant_is_authorised():
    from datetime import datetime, timedelta, timezone

    from agent.src.security.delegation import Delegation
    from agent.src.security.resolver import Identity as Id

    g = build_guard(
        config=config(),
        credentials=Connected(),
        servers=SERVERS,
        identity=Id(subject="ticket-triage", delegated_by="someone@example.com"),
        delegations=[
            Delegation(
                granter="someone@example.com",
                agent="ticket-triage",
                tools=["tracker.*"],
                servers=["tracker"],
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        ],
    )
    assert isinstance(g.authorise(CREATE), Allowed)


def test_untrusted_text_escalates_only_a_write_that_quotes_it():
    g = guard(precise_taint=True)
    g.record_result(
        ToolResult(tool_name="search", server="tracker"),
        text="replica lag in eu-west-1 exceeded 90 seconds",
    )

    unrelated = ToolCall(
        name="tracker.create_issue",
        server="tracker",
        writes=True,
        args={"title": "quarterly planning"},
    )
    quoting = ToolCall(
        name="tracker.create_issue",
        server="tracker",
        writes=True,
        args={"title": "replica lag in eu-west-1 exceeded 90 seconds"},
    )

    assert isinstance(g.authorise(unrelated), Allowed)
    assert isinstance(g.authorise(quoting), NeedsApproval)


def test_without_precise_taint_any_write_escalates():
    g = guard()
    g.record_result(
        ToolResult(tool_name="search", server="tracker"), text="anything at all"
    )
    unrelated = ToolCall(
        name="tracker.create_issue",
        server="tracker",
        writes=True,
        args={"title": "unrelated"},
    )
    assert isinstance(g.authorise(unrelated), NeedsApproval)


def test_a_trusted_result_reaches_the_model_unchanged():
    g = guard()
    assert (
        g.ingest(ToolResult(tool_name="list", server="docs"), text="plain") == "plain"
    )


def test_an_untrusted_result_is_fenced_before_the_model_sees_it():
    g = guard()
    fenced = g.ingest(ToolResult(tool_name="search", server="tracker"), text="plain")
    assert "plain" in fenced
    assert "tracker" in fenced
    assert "not instructions" in fenced.lower()


def test_a_local_result_is_not_fenced():
    g = guard()
    assert g.ingest(ToolResult(tool_name="read_file"), text="plain") == "plain"


def test_ingesting_untrusted_content_escalates_the_next_write():
    g = guard()
    g.ingest(ToolResult(tool_name="search", server="tracker"), text="plain")
    assert isinstance(g.authorise(CREATE), NeedsApproval)


def test_ingesting_trusted_content_leaves_writes_alone():
    g = guard()
    g.ingest(ToolResult(tool_name="list", server="docs"), text="plain")
    assert isinstance(g.authorise(CREATE), Allowed)


def test_ingested_text_is_remembered_for_precise_escalation():
    g = guard(precise_taint=True)
    g.ingest(
        ToolResult(tool_name="search", server="tracker"),
        text="replica lag in eu-west-1",
    )
    quoting = ToolCall(
        name="tracker.create_issue",
        server="tracker",
        writes=True,
        args={"title": "replica lag in eu-west-1"},
    )
    assert isinstance(g.authorise(quoting), NeedsApproval)
