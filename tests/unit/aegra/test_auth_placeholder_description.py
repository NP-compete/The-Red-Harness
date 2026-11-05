"""The placeholder's own description decided when it got called."""

from __future__ import annotations

from agent.aegra.mcp import _create_auth_placeholder_tool

DESC = _create_auth_placeholder_tool(
    "dataverse", {"description": "Dataverse data products, domains and ownership."}
).description


class TestItNoLongerDemandsToBeCalled:
    def test_there_is_no_unconditional_order(self):
        assert "MUST" not in DESC

    def test_calling_is_conditioned_on_actually_needing_the_data(self):
        assert "only when answering genuinely requires data" in DESC

    def test_capability_questions_are_named_as_a_non_reason(self):
        """The exact case that broke: 'what can you do for me?'."""
        lowered = DESC.lower()
        assert "what you can do" in lowered
        assert "own capabilities" in lowered

    def test_probing_for_availability_is_named_as_a_non_reason(self):
        assert "check whether it is available" in DESC


class TestItNoLongerPromisesSomethingUntrue:
    def test_it_does_not_claim_to_authenticate_on_its_own(self):
        """Mid-answer authorization was removed; the call reports that"""
        assert "automatically" not in DESC
        assert "NOT CONNECTED" in DESC


class TestTheServiceIsStillIdentifiable:
    def test_the_configured_description_survives(self):
        assert "Dataverse data products" in DESC

    def test_a_server_without_a_description_still_reads_sensibly(self):
        desc = _create_auth_placeholder_tool("miro", {}).description
        assert "miro services" in desc
