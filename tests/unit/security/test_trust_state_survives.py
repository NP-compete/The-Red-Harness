"""What a run read must outlive everything inside the run."""

from __future__ import annotations

import inspect

from agent.src.security.untrusted_reads import (
    forget_reads,
    note_untrusted_read,
    read_something_untrusted,
)


class TestASubagentDoesNotForget:
    def test_the_subagent_list_has_no_run_boundary_reset(self):
        from agent.src.infrastructure import subagents

        assert "build_fresh_run_middleware" not in inspect.getsource(subagents)

    def test_the_orchestrator_list_does(self):
        from agent.src.infrastructure import middleware

        assert "build_fresh_run_middleware" in inspect.getsource(
            middleware.build_middleware_list
        )

    def test_delegating_leaves_the_record_standing(self):
        forget_reads()
        note_untrusted_read("deploy is blocked on the migration", source="jira")

        from agent.src.infrastructure.subagents import _build_fallback_middleware

        built = _build_fallback_middleware.__doc__ or ""
        assert "fresh" not in built.lower()
        assert read_something_untrusted() is True
        forget_reads()


class TestCompactionCannotEraseIt:
    def test_the_record_is_not_held_in_the_messages(self):
        from agent.src.security import untrusted_reads

        assert "ContextVar" in inspect.getsource(untrusted_reads)

    def test_the_answer_does_not_depend_on_any_message(self):
        import inspect as _inspect

        assert _inspect.signature(read_something_untrusted).parameters == {}

    def test_it_survives_a_turn_that_rewrites_the_messages(self):
        import asyncio

        from agent.src.infrastructure.middleware import (
            build_nothing_to_send_middleware,
        )

        forget_reads()
        note_untrusted_read("deploy is blocked on the migration", source="jira")

        middleware = build_nothing_to_send_middleware()

        class _Request:
            messages = []
            system_message = ""

        async def _handler(_request):
            return "answered"

        if middleware is not None:
            asyncio.run(middleware.awrap_model_call(_Request(), _handler))

        assert read_something_untrusted() is True
        forget_reads()

    def test_only_the_run_boundary_clears_it(self):
        from agent.src.security import untrusted_reads

        source = inspect.getsource(untrusted_reads)
        assert source.count("_READS.set(None)") == 1
