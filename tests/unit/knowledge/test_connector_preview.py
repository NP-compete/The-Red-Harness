"""What connecting a source would let the agent read."""

from __future__ import annotations

import pytest

from agent.src.knowledge.connector_preview import Offer, preview


def offer(**kwargs) -> Offer:
    defaults = {
        "source": "drive",
        "folders": ("Team docs",),
        "documents": 240,
        "includes_shared_with_you": False,
        "includes_everything": False,
        "writes": (),
        "reads_as": "ada",
    }
    defaults.update(kwargs)
    return Offer(**defaults)


def test_the_folders_that_would_be_read_are_listed():
    assert preview(offer()).reads == ["Team docs"]


def test_how_much_would_be_read_is_counted():
    assert preview(offer()).documents == 240


def test_an_offer_covering_everything_says_so_rather_than_listing_folders():
    broad = offer(includes_everything=True, folders=("Team docs", "Personal"))
    assert preview(broad).reads == ["everything you can open"]


def test_an_offer_covering_everything_is_worth_a_warning():
    assert preview(offer(includes_everything=True)).warnings != []


def test_an_ordinary_folder_offer_warns_about_nothing():
    assert preview(offer()).warnings == []


def test_including_documents_shared_with_you_is_called_out():
    shared = offer(includes_shared_with_you=True)
    assert "documents other people shared with you" in preview(shared).warnings[0]


def test_an_offer_that_can_change_things_is_called_out():
    writing = offer(writes=("create files",))
    assert "create files" in preview(writing).warnings[0]


def test_the_account_the_agent_would_act_as_is_named():
    assert preview(offer()).acts_as == "ada"


def test_a_read_only_offer_is_marked_read_only():
    assert preview(offer()).read_only is True


def test_an_offer_that_writes_is_not_read_only():
    assert preview(offer(writes=("create files",))).read_only is False


def test_a_read_only_offer_of_one_folder_can_be_accepted_simply():
    assert preview(offer()).needs_careful_consent is False


def test_an_offer_covering_everything_needs_a_deliberate_yes():
    assert preview(offer(includes_everything=True)).needs_careful_consent is True


def test_an_offer_that_writes_needs_a_deliberate_yes():
    assert preview(offer(writes=("create files",))).needs_careful_consent is True


def test_every_warning_is_kept_not_just_the_first():
    busy = offer(
        includes_everything=True,
        includes_shared_with_you=True,
        writes=("delete files",),
    )
    assert len(preview(busy).warnings) == 3


def test_an_offer_of_nothing_at_all_is_refused():
    with pytest.raises(ValueError):
        offer(folders=(), includes_everything=False)


def test_a_negative_document_count_is_refused():
    with pytest.raises(ValueError):
        offer(documents=-1)
