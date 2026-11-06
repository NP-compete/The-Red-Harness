"""The artefact a person reviews (E12-T5)."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.src.improvement.review import review_body, thread_link, write_review


@dataclass
class FakeProbe:
    verdict: str = "sql was called 45 time(s) here and 34 of those fed an answer."
    touched: int = 45
    used: int = 34
    change: str = "sql is no longer offered"
    rerun: bool = False


@dataclass
class FakeProposal:
    kind: str = "tool_abandoned"
    detail: str = "sql was called and its result unused"
    argument: str = "Excluding it removes a tool the model is not using well."
    seen: int = 4
    runs: list = field(default_factory=lambda: ["t-1", "t-2"])
    path: str = "config/agent/runtime/agent.yaml"
    diff: str = "--- a/x\n+++ b/x\n+      - sql\n"
    permitted: bool = True
    refusal: str = ""
    blocked: str = ""
    probe: object = None


class TestTheBody:
    def test_it_carries_the_observation_and_the_count(self):
        body = review_body(FakeProposal())
        assert "sql was called and its result unused" in body
        assert "4 time(s)" in body

    def test_it_carries_the_diff(self):
        assert "+      - sql" in review_body(FakeProposal())

    def test_it_links_the_conversations_a_reviewer_can_open(self):
        body = review_body(FakeProposal(), ui_base="http://ui:5173")
        assert "http://ui:5173/chat/t-1" in body

    def test_the_probe_argues_against_the_change_in_the_same_body(self):
        body = review_body(FakeProposal(probe=FakeProbe()))
        assert "34 of those fed an answer" in body

    def test_it_says_nothing_was_re_run(self):
        body = review_body(FakeProposal(probe=FakeProbe()))
        assert "Nothing was re-run" in body

    def test_a_refusal_leads_with_the_refusal(self):
        body = review_body(
            FakeProposal(permitted=False, diff="", refusal="raises a cap")
        )
        assert "Refused by the control check" in body
        assert "raises a cap" in body

    def test_an_observation_with_no_mechanical_fix_says_so(self):
        body = review_body(
            FakeProposal(diff="", blocked="nothing here can write words")
        )
        assert "No change is proposed" in body
        assert "nothing here can write words" in body


class TestWhatIsWritten:
    def test_a_body_and_a_patch_per_proposal(self, tmp_path):
        written = write_review([FakeProposal()], out_dir=tmp_path)
        names = sorted(p.name for p in written)
        assert names == ["01-tool-abandoned.md", "01-tool-abandoned.patch", "index.md"]

    def test_the_patch_is_the_diff_alone(self, tmp_path):
        write_review([FakeProposal()], out_dir=tmp_path)
        assert (tmp_path / "01-tool-abandoned.patch").read_text().startswith("--- a/x")

    def test_a_refusal_gets_a_body_and_no_patch(self, tmp_path):
        written = write_review(
            [FakeProposal(permitted=False, diff="", refusal="raises a cap")],
            out_dir=tmp_path,
        )
        assert not [p for p in written if p.suffix == ".patch"]
        assert (tmp_path / "01-tool-abandoned.md").exists()

    def test_a_quiet_week_still_writes_an_index(self, tmp_path):
        write_review([], out_dir=tmp_path)
        assert "Nothing in the window read" in (tmp_path / "index.md").read_text()

    def test_the_index_flags_the_one_the_probe_argues_against(self, tmp_path):
        write_review([FakeProposal(probe=FakeProbe())], out_dir=tmp_path)
        assert "probe argues against it" in (tmp_path / "index.md").read_text()


class TestLinks:
    def test_without_a_base_the_id_is_the_link(self):
        assert thread_link("t-1", "") == "t-1"

    def test_a_trailing_slash_does_not_double(self):
        assert thread_link("t-1", "http://ui/") == "http://ui/chat/t-1"
