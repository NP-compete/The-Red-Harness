"""A trace names the run, not only the conversation (OBS-1)."""

from __future__ import annotations

import pytest

from agent.aegra.telemetry import (
    LangfuseObservabilityProvider,
    TokenBudgetObservabilityProvider,
)


@pytest.fixture
def metadata():
    return LangfuseObservabilityProvider().get_metadata(
        run_id="run-7", thread_id="thread-3", user_identity="ada"
    )


class TestWhatReachesTheTrace:
    def test_the_run(self, metadata):
        assert metadata["run_id"] == "run-7"

    def test_the_conversation(self, metadata):
        assert metadata["langfuse_session_id"] == "thread-3"
        assert metadata["thread_id"] == "thread-3"

    def test_the_user(self, metadata):
        assert metadata["langfuse_user_id"]

    def test_pseudonymised_where_a_deployment_asked_for_it(self, monkeypatch):
        """`encrypt_user_id` sits between the identity and the trace."""
        from agent.aegra import auth

        monkeypatch.setattr(auth, "ENABLE_USER_ID_ENCRYPTION", True)
        monkeypatch.setattr(auth, "USER_ID_ENCRYPTION_KEY", "a-key")

        said = LangfuseObservabilityProvider().get_metadata(
            run_id="run-7", thread_id="thread-3", user_identity="ada"
        )
        assert said["langfuse_user_id"] != "ada"

    def test_and_is_the_identity_when_nobody_did(self, metadata):
        assert metadata["langfuse_user_id"] == "ada"

    def test_the_trace_id_when_a_request_bound_one(self):
        from agent.utils.pylogger import (
            bind_request_context,
            clear_request_context,
        )

        try:
            bind_request_context(trace_id="tr-9")
            said = LangfuseObservabilityProvider().get_metadata(
                run_id="run-7", thread_id="thread-3", user_identity="ada"
            )
            assert said["trace_id"] == "tr-9"
        finally:
            clear_request_context()


class TestWhatItLeavesOut:
    def test_no_run_means_no_key(self):
        said = LangfuseObservabilityProvider().get_metadata(
            run_id="", thread_id="thread-3", user_identity="ada"
        )
        assert "run_id" not in said

    def test_no_user_means_no_key(self):
        said = LangfuseObservabilityProvider().get_metadata(
            run_id="run-7", thread_id="thread-3", user_identity=None
        )
        assert "langfuse_user_id" not in said


class TestTheTokenBudgetProviderToo:
    """The other provider on the same registry."""

    def test_it_carries_the_thread_and_the_user(self):
        said = TokenBudgetObservabilityProvider().get_metadata(
            run_id="run-7", thread_id="thread-3", user_identity="ada"
        )
        assert "thread-3" in said.values()
        assert "ada" in said.values()

    def test_and_deliberately_not_the_run(self):
        said = TokenBudgetObservabilityProvider().get_metadata(
            run_id="run-7", thread_id="thread-3", user_identity="ada"
        )
        assert "run-7" not in said.values(), (
            "the token-budget provider started carrying the run. If that is "
            "wanted, say so here — the budget is per thread, so the run was "
            "left out on purpose."
        )
