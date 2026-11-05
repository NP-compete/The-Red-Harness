"""Answering an approval from a terminal (E28-T5)."""

from __future__ import annotations

from agent.cli.approve import decide, describe

WAITING = {
    "status": "needs_approval",
    "awaiting": [
        {
            "action": "send_email",
            "args": {"to": "ada@example.com", "subject": "hello"},
            "description": "[HIGH RISK] send_email: posts to a third party",
        }
    ],
    "resume": {"thread_id": "t-1", "decisions": ["approve", "reject"]},
}


class TestWhatThePersonIsShown:
    def test_the_risk_and_the_reason_come_with_it(self):
        said = describe(WAITING["awaiting"][0])
        assert "HIGH RISK" in said and "third party" in said

    def test_so_do_the_arguments(self):
        assert "ada@example.com" in describe(WAITING["awaiting"][0])

    def test_an_unreadable_request_still_prints_something(self):
        assert describe({}) == "unknown"


class TestWithNobodyThere:
    def test_no_decision_is_invented(self):
        assert decide(WAITING, interactive=False) is None


class TestWithSomebodyThere:
    def test_approve_is_sent(self):
        found = decide(
            WAITING, interactive=True, ask=lambda _p: "approve", write=lambda _l: None
        )
        assert found.decision == "approve" and not found.automatic

    def test_reject_carries_the_reason_back(self):
        answers = iter(["reject", "we do not email customers"])
        found = decide(
            WAITING,
            interactive=True,
            ask=lambda _p: next(answers),
            write=lambda _l: None,
        )
        assert found.decision == "reject"
        assert found.message == "we do not email customers"

    def test_a_mistyped_answer_is_neither(self):
        said: list[str] = []
        assert (
            decide(WAITING, interactive=True, ask=lambda _p: "yes", write=said.append)
            is None
        )
        assert any("nothing was sent" in line for line in said)

    def test_the_offered_decisions_come_from_the_agent(self):
        said: list[str] = []
        waiting = {
            **WAITING,
            "resume": {"thread_id": "t-1", "decisions": ["approve", "edit", "reject"]},
        }
        decide(
            waiting,
            interactive=True,
            ask=lambda p: said.append(p) or "edit",
            write=lambda _l: None,
        )
        assert "edit" in said[0]


class TestAutomatically:
    def test_every_action_it_approved_is_named(self):
        said: list[str] = []
        found = decide(WAITING, approve_all=True, write=said.append)
        assert found.decision == "approve" and found.automatic
        assert "send_email" in said[0]

    def test_it_does_not_ask(self):
        def refuse(_prompt):
            raise AssertionError("asked anyway")

        assert decide(
            WAITING, approve_all=True, ask=refuse, write=lambda _l: None
        ).automatic


class TestWhatIsNotClaimed:
    def test_the_gap_in_the_audit_trail_is_written_down(self):
        from agent.cli.approve import NOT_AUDITED

        assert "audit trail" in NOT_AUDITED
