"""Choosing what to summarise when a conversation outgrows its window."""

from __future__ import annotations

from agent.src.agent.compaction import Message, plan_compaction


def msg(role="user", text="hello", tokens=10, **kwargs) -> Message:
    return Message(role=role, text=text, tokens=tokens, **kwargs)


def test_a_short_conversation_is_left_alone():
    assert plan_compaction([msg(), msg()], limit_tokens=1000) is None


def test_a_conversation_over_the_threshold_is_compacted():
    assert (
        plan_compaction([msg(tokens=400) for _ in range(3)], limit_tokens=1000)
        is not None
    )


def test_the_system_message_is_never_summarised():
    messages = [msg(role="system", tokens=400)] + [msg(tokens=400) for _ in range(3)]
    plan = plan_compaction(messages, limit_tokens=1000)
    assert messages[0] not in plan.summarise
    assert messages[0] in plan.keep


def test_the_most_recent_turns_are_kept_verbatim():
    messages = [msg(text=str(i), tokens=400) for i in range(6)]
    plan = plan_compaction(messages, limit_tokens=1000, keep_recent=2)
    assert plan.keep[-2:] == messages[-2:]


def test_a_message_awaiting_approval_is_never_summarised():
    pending = msg(text="pending", tokens=400, awaiting_approval=True)
    messages = [msg(tokens=400), pending] + [msg(tokens=400) for _ in range(3)]
    plan = plan_compaction(messages, limit_tokens=1000, keep_recent=1)
    assert pending not in plan.summarise
    assert pending in plan.keep


def test_order_is_preserved_in_what_is_kept():
    messages = [msg(text=str(i), tokens=400) for i in range(6)]
    plan = plan_compaction(messages, limit_tokens=1000, keep_recent=2)
    kept = [m.text for m in plan.keep]
    assert kept == sorted(kept, key=lambda t: [m.text for m in messages].index(t))


def test_nothing_is_both_kept_and_summarised():
    messages = [msg(text=str(i), tokens=400) for i in range(6)]
    plan = plan_compaction(messages, limit_tokens=1000, keep_recent=2)
    assert not set(id(m) for m in plan.keep) & set(id(m) for m in plan.summarise)


def test_the_summary_inherits_the_lowest_trust_of_its_inputs():
    messages = [
        msg(tokens=400, trusted=True),
        msg(tokens=400, trusted=False),
        msg(tokens=400, trusted=True),
    ] + [msg(tokens=400) for _ in range(2)]
    plan = plan_compaction(messages, limit_tokens=1000, keep_recent=2)
    assert plan.summary_is_trusted is False


def test_a_summary_of_trusted_input_stays_trusted():
    messages = [msg(tokens=400, trusted=True) for _ in range(5)]
    plan = plan_compaction(messages, limit_tokens=1000, keep_recent=2)
    assert plan.summary_is_trusted is True


def test_nothing_is_compacted_when_only_protected_messages_are_old():
    messages = [msg(role="system", tokens=900), msg(tokens=400), msg(tokens=400)]
    assert plan_compaction(messages, limit_tokens=1000, keep_recent=2) is None


def test_the_threshold_is_a_fraction_of_the_limit():
    messages = [msg(tokens=200) for _ in range(4)]
    assert plan_compaction(messages, limit_tokens=1000, trigger_at=0.5) is not None
    assert plan_compaction(messages, limit_tokens=1000, trigger_at=0.95) is None


class TestASkillStays:
    """Skills in play are not conversation; they are what the agent"""

    def test_a_skill_is_never_summarised(self):
        skill = msg(text="skill", tokens=400, is_skill=True)
        messages = [skill] + [msg(tokens=400) for _ in range(3)]
        plan = plan_compaction(messages, limit_tokens=1000)
        assert skill not in plan.summarise

    def test_a_skill_is_kept_verbatim(self):
        skill = msg(text="skill", tokens=400, is_skill=True)
        messages = [skill] + [msg(tokens=400) for _ in range(3)]
        assert skill in plan_compaction(messages, limit_tokens=1000).keep

    def test_a_thread_of_nothing_but_skills_is_left_alone(self):
        messages = [msg(tokens=400, is_skill=True) for _ in range(3)]
        assert plan_compaction(messages, limit_tokens=1000) is None


class TestAToolCallIsNotSplitFromItsResult:
    """A call whose result has been summarised away is not a shorter"""

    def _exchange(self, call_id="c1", tokens=400):
        return [
            msg(role="assistant", text="calling", tokens=tokens, tool_call_id=call_id),
            msg(role="tool", text="result", tokens=tokens, tool_call_id=call_id),
        ]

    def test_the_result_is_kept_when_the_call_is(self):
        pair = self._exchange()
        messages = [msg(tokens=400) for _ in range(3)] + pair
        plan = plan_compaction(messages, limit_tokens=1000, keep_recent=1)
        assert pair[0] in plan.keep and pair[1] in plan.keep

    def test_the_call_is_kept_when_the_result_is(self):
        caller = msg(role="assistant", text="calling", tokens=400, tool_call_id="c2")
        held = msg(
            role="tool",
            text="result",
            tokens=400,
            tool_call_id="c2",
            awaiting_approval=True,
        )
        messages = [caller, held] + [msg(tokens=400) for _ in range(4)]
        plan = plan_compaction(messages, limit_tokens=1000, keep_recent=1)
        assert caller in plan.keep and held in plan.keep

    def test_a_whole_exchange_may_still_be_summarised(self):
        pair = self._exchange()
        messages = pair + [msg(tokens=400) for _ in range(4)]
        plan = plan_compaction(messages, limit_tokens=1000, keep_recent=1)
        assert pair[0] in plan.summarise and pair[1] in plan.summarise

    def test_an_exchange_is_never_half_summarised(self):
        pair = self._exchange()
        messages = [msg(tokens=400)] + pair + [msg(tokens=400) for _ in range(2)]
        plan = plan_compaction(messages, limit_tokens=1000, keep_recent=2)
        assert (pair[0] in plan.summarise) == (pair[1] in plan.summarise)


class TestTheSummaryIsDataNotInstruction:
    """A summary is made out of what was said to the agent and what"""

    def test_the_summary_does_not_speak_as_the_system(self):
        from agent.src.agent.compaction import apply_compaction

        messages = [msg(role="system", tokens=400)] + [
            msg(tokens=400) for _ in range(3)
        ]
        plan = plan_compaction(messages, limit_tokens=1000)
        out = apply_compaction(messages, plan, summary="they talked")
        stand_in = next(m for m in out if m.is_summary)
        assert stand_in.role != "system"

    def test_the_system_prompt_is_still_the_first_thing(self):
        from agent.src.agent.compaction import apply_compaction

        messages = [msg(role="system", tokens=400)] + [
            msg(tokens=400) for _ in range(3)
        ]
        plan = plan_compaction(messages, limit_tokens=1000)
        out = apply_compaction(messages, plan, summary="they talked")
        assert out[0].role == "system" and not out[0].is_summary
