"""Whether a document may be taken into the knowledge base."""

from __future__ import annotations

import pytest

from agent.src.knowledge.ingestion_policy import Document, Refusal, may_ingest


def document(**kwargs) -> Document:
    defaults = {
        "name": "handbook.pdf",
        "bytes": 2_000_000,
        "kind": "document",
        "classification": "internal",
        "licence": "owned",
        "contains_personal_data": False,
        "scanned": True,
        "safe": True,
    }
    defaults.update(kwargs)
    return Document(**defaults)


def test_an_ordinary_document_may_be_taken_in():
    assert may_ingest(document()).permitted is True


def test_something_that_failed_its_scan_is_refused():
    assert may_ingest(document(safe=False)).refusal is Refusal.UNSAFE


def test_something_not_yet_scanned_is_refused():
    assert may_ingest(document(scanned=False)).refusal is Refusal.NOT_SCANNED


def test_an_unscanned_document_may_be_taken_in_once_scanned():
    assert may_ingest(document(scanned=False)).retry_after_scan is True


def test_an_unsafe_document_is_not_worth_scanning_again():
    assert may_ingest(document(safe=False)).retry_after_scan is False


def test_a_restricted_document_is_refused():
    assert (
        may_ingest(document(classification="restricted")).refusal
        is Refusal.CLASSIFICATION
    )


def test_a_document_nobody_may_copy_is_refused():
    assert may_ingest(document(licence="third-party")).refusal is Refusal.LICENCE


def test_a_document_licensed_for_use_is_allowed():
    assert may_ingest(document(licence="licensed")).permitted is True


def test_a_document_holding_personal_data_is_refused_as_it_stands():
    assert (
        may_ingest(document(contains_personal_data=True)).refusal
        is Refusal.PERSONAL_DATA
    )


def test_personal_data_may_be_removed_first():
    assert (
        may_ingest(document(contains_personal_data=True), scrubbed=True).permitted
        is True
    )


def test_scrubbing_does_not_rescue_a_restricted_document():
    restricted = document(classification="restricted", contains_personal_data=True)
    assert may_ingest(restricted, scrubbed=True).permitted is False


def test_a_document_too_large_is_refused():
    assert may_ingest(document(bytes=200_000_000)).refusal is Refusal.TOO_LARGE


def test_a_kind_that_cannot_be_read_is_refused():
    assert may_ingest(document(kind="program")).refusal is Refusal.UNREADABLE


def test_safety_is_checked_before_anything_about_the_contents():
    unsafe = document(safe=False, classification="restricted", bytes=200_000_000)
    assert may_ingest(unsafe).refusal is Refusal.UNSAFE


def test_a_refusal_says_what_would_make_it_acceptable():
    assert "scrub" in may_ingest(document(contains_personal_data=True)).reason


def test_a_permitted_document_has_nothing_to_say():
    assert may_ingest(document()).reason == ""


def test_an_unknown_classification_is_refused():
    with pytest.raises(ValueError):
        document(classification="whatever")


def test_a_document_with_no_name_is_refused():
    with pytest.raises(ValueError):
        document(name="   ")
