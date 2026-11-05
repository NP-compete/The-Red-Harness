"""Runs, for whoever is holding the pager."""

from __future__ import annotations

import pytest

from agent.cli.runs import RunFailed, cancel_run, list_runs, show_run

LISTED = [
    {
        "run_id": "r1",
        "status": "success",
        "error_message": None,
        "created_at": "2026-10-28T10:00:00Z",
    },
    {
        "run_id": "r2",
        "status": "error",
        "error_message": "the model refused",
        "created_at": "2026-10-28T10:05:00Z",
    },
]


class _Transport:
    def __init__(self, replies):
        self._replies = replies
        self.calls: list[tuple[str, str]] = []

    def _answer(self, method, path):
        self.calls.append((method, path))
        return self._replies.get((method, path), (404, {"detail": "not found"}))

    def get(self, path):
        return self._answer("GET", path)

    def post(self, path, body=None):
        return self._answer("POST", path)

    def delete(self, path):
        return self._answer("DELETE", path)


class TestListing:
    def _listed(self, payload=LISTED, status=200):
        transport = _Transport({("GET", "/threads/t1/runs"): (status, payload)})
        return list_runs("t1", transport=transport)

    def test_it_reports_each_run(self):
        assert len(self._listed()) == 2

    def test_it_reports_what_the_agent_says_about_each(self):
        assert self._listed()[1].status == "error"

    def test_it_carries_why_one_failed(self):
        assert self._listed()[1].error == "the model refused"

    def test_a_run_that_did_not_fail_carries_no_reason(self):
        assert self._listed()[0].error == ""

    def test_it_reports_when_each_started(self):
        assert self._listed()[0].created_at.startswith("2026-10-28")

    def test_a_refusal_is_not_an_empty_list(self):
        with pytest.raises(RunFailed):
            self._listed(payload={"detail": "no"}, status=403)

    def test_the_wrapped_shape_is_read_too(self):
        assert len(self._listed(payload={"runs": LISTED})) == 2


class TestShowing:
    def test_it_returns_the_run(self):
        transport = _Transport(
            {("GET", "/threads/t1/runs/r1"): (200, {"run_id": "r1"})}
        )
        assert show_run("t1", "r1", transport=transport)["run_id"] == "r1"

    def test_a_run_that_is_not_there_is_reported(self):
        with pytest.raises(RunFailed, match="r9"):
            show_run("t1", "r9", transport=_Transport({}))


class TestCancelling:
    def test_it_asks_the_agent_to_stop(self):
        transport = _Transport({("POST", "/threads/t1/runs/r1/cancel"): (200, {})})
        cancel_run("t1", "r1", transport=transport)
        assert ("POST", "/threads/t1/runs/r1/cancel") in transport.calls

    def test_a_refusal_is_reported_rather_than_assumed_to_have_worked(self):
        transport = _Transport(
            {("POST", "/threads/t1/runs/r1/cancel"): (409, {"detail": "finished"})}
        )
        with pytest.raises(RunFailed, match="finished"):
            cancel_run("t1", "r1", transport=transport)

    def test_cancelling_one_that_is_already_gone_is_not_an_error(self):
        transport = _Transport({("POST", "/threads/t1/runs/r1/cancel"): (404, {})})
        cancel_run("t1", "r1", transport=transport)


class TestWhatIsStuck:
    """The question behind the command."""

    @staticmethod
    def _stuck(rows):
        from agent.cli.runs import unfinished

        return unfinished([_row(r) for r in rows])

    def test_a_running_one_counts(self):
        assert len(self._stuck([{"run_id": "r1", "status": "running"}])) == 1

    def test_a_pending_one_counts(self):
        assert len(self._stuck([{"run_id": "r1", "status": "pending"}])) == 1

    def test_a_finished_one_does_not(self):
        assert self._stuck([{"run_id": "r1", "status": "success"}]) == []

    def test_a_failed_one_does_not(self):
        assert self._stuck([{"run_id": "r1", "status": "error"}]) == []

    def test_a_status_nobody_recognises_counts_as_stuck(self):
        assert len(self._stuck([{"run_id": "r1", "status": "wedged"}])) == 1


def _row(raw):
    from agent.cli.runs import RunRow

    return RunRow(
        run_id=raw["run_id"],
        status=raw.get("status", ""),
        error=raw.get("error_message") or "",
        created_at=raw.get("created_at", ""),
    )
