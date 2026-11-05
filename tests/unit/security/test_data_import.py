"""Taking in a file of someone else's data."""

from __future__ import annotations

import pytest

from agent.src.security.data_import import Batch, Verdict, admit_import


def batch(**kwargs) -> Batch:
    defaults = {
        "rows": 500,
        "rows_malformed": 0,
        "declared_rows": 500,
        "from_outside": False,
        "contains_personal_data": False,
        "consent_recorded": False,
        "scanned": True,
        "scan_clean": True,
        "importer_may_import": True,
    }
    defaults.update(kwargs)
    return Batch(**defaults)


def test_a_clean_batch_is_taken():
    assert admit_import(batch()).verdict is Verdict.ACCEPT


def test_an_unscanned_batch_is_never_taken():
    assert admit_import(batch(scanned=False)).verdict is Verdict.REFUSE


def test_a_batch_that_failed_its_scan_is_refused():
    assert admit_import(batch(scan_clean=False)).verdict is Verdict.REFUSE


def test_the_scan_is_checked_before_anything_in_the_file_is_read():
    dirty = batch(scanned=False, rows_malformed=500)
    assert "scanned" in admit_import(dirty).reason


def test_someone_without_permission_cannot_import():
    assert admit_import(batch(importer_may_import=False)).verdict is Verdict.REFUSE


def test_personal_data_without_recorded_consent_is_held_for_approval():
    personal = batch(contains_personal_data=True)
    assert admit_import(personal).verdict is Verdict.HOLD


def test_personal_data_with_recorded_consent_is_taken():
    personal = batch(contains_personal_data=True, consent_recorded=True)
    assert admit_import(personal).verdict is Verdict.ACCEPT


def test_a_few_malformed_rows_are_skipped_rather_than_failing_the_batch():
    patchy = batch(rows_malformed=5)
    assert admit_import(patchy).verdict is Verdict.ACCEPT


def test_the_rows_that_would_be_taken_are_counted():
    patchy = batch(rows_malformed=5)
    assert admit_import(patchy).rows_taken == 495


def test_a_batch_that_is_mostly_malformed_is_refused():
    broken = batch(rows_malformed=300)
    assert admit_import(broken).verdict is Verdict.REFUSE


def test_a_file_shorter_than_it_claims_is_refused():
    truncated = batch(rows=300, declared_rows=500)
    assert admit_import(truncated).verdict is Verdict.REFUSE


def test_a_truncated_file_says_so():
    truncated = batch(rows=300, declared_rows=500)
    assert "incomplete" in admit_import(truncated).reason


def test_data_from_outside_is_marked_untrusted_even_when_accepted():
    outside = batch(from_outside=True)
    assert admit_import(outside).trusted is False


def test_data_from_inside_is_trusted():
    assert admit_import(batch()).trusted is True


def test_data_from_outside_is_still_accepted():
    assert admit_import(batch(from_outside=True)).verdict is Verdict.ACCEPT


def test_a_refusal_always_says_why():
    assert admit_import(batch(scan_clean=False)).reason


def test_an_accepted_batch_needs_no_explanation():
    assert admit_import(batch()).reason == ""


def test_an_empty_batch_is_refused():
    with pytest.raises(ValueError):
        batch(rows=0, declared_rows=0)


def test_more_malformed_rows_than_rows_is_refused():
    with pytest.raises(ValueError):
        batch(rows=10, declared_rows=10, rows_malformed=11)
