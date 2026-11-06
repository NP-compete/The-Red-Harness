"""Whether what a call is about to send came from something untrusted."""

from __future__ import annotations

from agent.src.security.taint import TaintLedger


def ledger(*fragments: str, min_length: int = 12) -> TaintLedger:
    led = TaintLedger(min_length=min_length)
    for fragment in fragments:
        led.record(fragment)
    return led


def test_nothing_is_derived_from_an_empty_ledger():
    assert TaintLedger().derives({"title": "anything at all"}) is False


def test_an_argument_lifted_from_untrusted_output_is_derived():
    led = ledger("replica lag in eu-west-1 exceeded 90 seconds")
    assert (
        led.derives({"title": "replica lag in eu-west-1 exceeded 90 seconds"}) is True
    )


def test_a_fragment_embedded_in_a_longer_argument_is_derived():
    led = ledger("replica lag in eu-west-1")
    assert (
        led.derives({"body": "Runbook needed: replica lag in eu-west-1 again"}) is True
    )


def test_unrelated_arguments_are_not_derived():
    led = ledger("replica lag in eu-west-1")
    assert led.derives({"title": "quarterly planning notes"}) is False


def test_short_fragments_are_ignored_to_avoid_false_positives():
    led = ledger("the")
    assert led.derives({"title": "the quarterly review"}) is False


def test_nested_arguments_are_searched():
    led = ledger("token store exhaustion")
    assert led.derives({"issue": {"fields": ["token store exhaustion"]}}) is True


def test_non_text_arguments_are_ignored():
    led = ledger("token store exhaustion")
    assert led.derives({"count": 5, "flag": True, "nothing": None}) is False


def test_matching_ignores_surrounding_whitespace_and_case():
    led = ledger("Token Store Exhaustion")
    assert led.derives({"title": "  token store exhaustion  "}) is True


def test_recording_is_cumulative():
    led = ledger("replica lag in eu-west-1")
    led.record("token store exhaustion")
    assert led.derives({"title": "token store exhaustion"}) is True


def test_it_reports_what_tainted_the_call():
    led = ledger("token store exhaustion")
    assert led.matched({"title": "token store exhaustion here"}) == (
        "token store exhaustion",
    )


def test_nothing_matched_when_nothing_derives():
    assert ledger("token store exhaustion").matched({"title": "unrelated"}) == ()


class TestAskingWhetherAnythingWasRecorded:
    """A caller should not have to reach inside to find out."""

    def test_a_new_ledger_holds_nothing(self):
        from agent.src.security.taint import TaintLedger

        assert TaintLedger().holds_anything() is False

    def test_a_recorded_fragment_shows(self):
        from agent.src.security.taint import TaintLedger

        ledger = TaintLedger()
        ledger.record("deploy is blocked on the migration")
        assert ledger.holds_anything() is True

    def test_something_too_short_to_keep_does_not(self):
        from agent.src.security.taint import TaintLedger

        ledger = TaintLedger()
        ledger.record("ok")
        assert ledger.holds_anything() is False


class TestAWriteThatEchoesOneLine:
    """Matched per line, because that is what gets echoed."""

    @staticmethod
    def _ledger(text):
        from agent.src.security.taint import TaintLedger

        ledger = TaintLedger()
        ledger.record(text)
        return ledger

    def test_a_quoted_line_is_found(self):
        ledger = self._ledger(
            "Ticket 41: status open\ndeploy is blocked on the migration\nowner: sam"
        )
        found = ledger.matched(
            {"body": "Per the ticket: deploy is blocked on the migration"}
        )
        assert "deploy is blocked on the migration" in found

    def test_the_whole_result_still_matches_when_it_is_repeated(self):
        ledger = self._ledger("deploy is blocked on the migration")
        assert ledger.matched({"body": "deploy is blocked on the migration"})

    def test_a_short_line_is_not_kept(self):
        ledger = self._ledger("open\nowner: sam\ndeploy is blocked on the migration")
        assert ledger.matched({"body": "the door is open"}) == ()

    def test_an_unrelated_write_matches_nothing(self):
        ledger = self._ledger("deploy is blocked on the migration")
        assert ledger.matched({"body": "unrelated text entirely"}) == ()

    def test_blank_lines_are_not_kept(self):
        ledger = self._ledger("a\n\n   \nb")
        assert ledger.holds_anything() is False
