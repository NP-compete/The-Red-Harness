"""The corpus an agent ships with, read from its configuration tree."""

from __future__ import annotations

import pytest

from agent.src.knowledge.ingest import Progress, sync_corpus
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import InMemoryStore

ANYONE = Viewer(subject="alice", teams=(), thread_id=None)


def _tree(tmp_path, files: dict[str, str]):
    root = tmp_path / "knowledge"
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _ids(store) -> set[str]:
    return {d.id for d in store.search("policy", scope=Scope.AGENT, viewer=ANYONE)}


class TestReadingTheTree:
    def test_a_document_is_ingested(self, tmp_path):
        store = InMemoryStore()
        sync_corpus(_tree(tmp_path, {"handbook.md": "the policy is 750"}), store=store)
        assert _ids(store)

    def test_several_are(self, tmp_path):
        store = InMemoryStore()
        sync_corpus(
            _tree(tmp_path, {"a.md": "policy one", "b.md": "policy two"}), store=store
        )
        assert len(_ids(store)) == 2

    def test_documents_in_subdirectories_are_found(self, tmp_path):
        store = InMemoryStore()
        sync_corpus(_tree(tmp_path, {"hr/leave.md": "policy on leave"}), store=store)
        assert _ids(store)

    def test_the_identifier_is_the_path_in_the_tree(self, tmp_path):
        store = InMemoryStore()
        sync_corpus(_tree(tmp_path, {"hr/leave.md": "policy on leave"}), store=store)
        assert any("hr/leave.md" in found for found in _ids(store))

    def test_a_tree_that_is_not_there_is_not_an_error(self, tmp_path):
        store = InMemoryStore()
        found = sync_corpus(tmp_path / "nothing", store=store)
        assert found.ingested == 0

    def test_everything_lands_in_agent_scope(self, tmp_path):
        store = InMemoryStore()
        sync_corpus(_tree(tmp_path, {"a.md": "policy one"}), store=store)
        assert store.search("policy", scope=Scope.USER, viewer=ANYONE) == []


class TestItIsASyncNotAnAppend:
    """The property that keeps the corpus honest."""

    def test_a_file_removed_from_the_tree_leaves_the_store(self, tmp_path):
        store = InMemoryStore()
        root = _tree(tmp_path, {"a.md": "policy one", "b.md": "policy two"})
        sync_corpus(root, store=store)

        (root / "b.md").unlink()
        sync_corpus(root, store=store)
        assert len(_ids(store)) == 1

    def test_the_one_still_there_stays(self, tmp_path):
        store = InMemoryStore()
        root = _tree(tmp_path, {"a.md": "policy one", "b.md": "policy two"})
        sync_corpus(root, store=store)
        (root / "b.md").unlink()
        sync_corpus(root, store=store)
        assert any("a.md" in found for found in _ids(store))

    def test_an_emptied_tree_empties_the_corpus(self, tmp_path):
        store = InMemoryStore()
        root = _tree(tmp_path, {"a.md": "policy one"})
        sync_corpus(root, store=store)
        (root / "a.md").unlink()
        sync_corpus(root, store=store)
        assert _ids(store) == set()

    def test_it_does_not_touch_anybody_elses_documents(self, tmp_path):
        from agent.src.knowledge.store import Document

        store = InMemoryStore()
        store.add(
            Document(id="u1", text="policy mine", scope=Scope.USER, owner="alice")
        )
        root = _tree(tmp_path, {"a.md": "policy one"})
        sync_corpus(root, store=store)
        (root / "a.md").unlink()
        sync_corpus(root, store=store)
        assert store.search("policy", scope=Scope.USER, viewer=ANYONE)

    def test_a_changed_file_is_reindexed_rather_than_duplicated(self, tmp_path):
        store = InMemoryStore()
        root = _tree(tmp_path, {"a.md": "policy one"})
        sync_corpus(root, store=store)
        (root / "a.md").write_text("policy two")
        sync_corpus(root, store=store)
        assert len(_ids(store)) == 1

    def test_and_the_new_text_is_what_is_found(self, tmp_path):
        store = InMemoryStore()
        root = _tree(tmp_path, {"a.md": "policy one"})
        sync_corpus(root, store=store)
        (root / "a.md").write_text("policy revised")
        sync_corpus(root, store=store)
        found = store.search("revised", scope=Scope.AGENT, viewer=ANYONE)
        assert found


class TestWhatItWillNotIngest:
    def test_a_file_with_no_text_is_skipped(self, tmp_path):
        store = InMemoryStore()
        found = sync_corpus(_tree(tmp_path, {"a.md": "   "}), store=store)
        assert found.ingested == 0

    def test_a_file_too_large_is_split_rather_than_skipped(self, tmp_path):
        store = InMemoryStore()
        found = sync_corpus(
            _tree(tmp_path, {"a.md": "policy " * 100}), store=store, max_bytes=10
        )
        assert found.skipped == []
        assert found.ingested == 1

    def test_the_whole_of_a_large_file_is_searchable(self, tmp_path):
        store = InMemoryStore()
        text = " ".join(f"clause{n}" for n in range(500))
        sync_corpus(_tree(tmp_path, {"big.md": text}), store=store, max_bytes=10)
        joined = " ".join(d.text for d in store.documents_in(scope=Scope.AGENT))
        assert "clause0" in joined
        assert "clause499" in joined

    def test_a_file_that_is_not_a_document_is_never_considered(self, tmp_path):
        store = InMemoryStore()
        root = _tree(tmp_path, {"a.md": "policy one"})
        (root / "b.bin").write_bytes(b"\x00\x01")
        found = sync_corpus(root, store=store)
        assert found.ingested == 1 and found.skipped == []

    def test_a_document_it_cannot_decode_does_not_stop_the_rest(self, tmp_path):
        store = InMemoryStore()
        root = _tree(tmp_path, {"a.md": "policy one"})
        (root / "broken.md").write_bytes(b"\xff\xfe\x00bad")
        found = sync_corpus(root, store=store)
        assert found.ingested == 1

    def test_and_the_one_it_could_not_read_is_named(self, tmp_path):
        store = InMemoryStore()
        root = _tree(tmp_path, {"a.md": "policy one"})
        (root / "broken.md").write_bytes(b"\xff\xfe\x00bad")
        found = sync_corpus(root, store=store)
        assert any("broken.md" in reason for reason in found.skipped)


class TestProgress:
    def test_it_reports_how_many_were_ingested(self, tmp_path):
        store = InMemoryStore()
        found = sync_corpus(_tree(tmp_path, {"a.md": "policy one"}), store=store)
        assert found.ingested == 1

    def test_it_reports_how_many_were_removed(self, tmp_path):
        store = InMemoryStore()
        root = _tree(tmp_path, {"a.md": "policy one"})
        sync_corpus(root, store=store)
        (root / "a.md").unlink()
        assert sync_corpus(root, store=store).removed == 1

    def test_it_is_observable_while_it_runs(self, tmp_path):
        seen: list[Progress] = []
        store = InMemoryStore()
        sync_corpus(
            _tree(tmp_path, {"a.md": "policy one", "b.md": "policy two"}),
            store=store,
            on_progress=seen.append,
        )
        assert len(seen) >= 2

    def test_progress_says_what_it_is_working_on(self, tmp_path):
        seen: list[Progress] = []
        store = InMemoryStore()
        sync_corpus(
            _tree(tmp_path, {"a.md": "policy one"}),
            store=store,
            on_progress=seen.append,
        )
        assert "a.md" in seen[-1].current


class TestItDoesNotHoldUpReadiness:
    def test_the_startup_sequence_actually_calls_it(self):
        import inspect

        from agent.aegra.startup import run_startup

        assert "start_corpus_ingestion" in inspect.getsource(run_startup)

    def test_it_does_not_await_the_corpus(self):
        import inspect

        from agent.aegra.startup import run_startup

        source = inspect.getsource(run_startup)
        assert "await start_corpus_ingestion" not in source

    def test_kicking_it_off_returns_without_a_corpus_configured(self, monkeypatch):
        from agent.aegra import startup

        # Say "no corpus" outright. This used to rely on the shipped
        # tree having the library off; it ships on, so the call got
        # past the guard and returned "no loop" instead.
        monkeypatch.setattr(startup, "_corpus_root", lambda: None)
        assert "not enabled" in startup.start_corpus_ingestion()

    @pytest.mark.asyncio
    async def test_a_corpus_that_fails_does_not_stop_the_agent(self):
        from agent.aegra.startup import _ingest_corpus_in_background

        class _Broken:
            def add(self, document):
                raise ConnectionError("store unavailable")

        await _ingest_corpus_in_background(root=None, store=_Broken())


class TestACorpusForOneTeam:
    """A directory per team, under `teams/`."""

    @staticmethod
    def _member(team: str):
        from agent.src.knowledge.scopes import Viewer

        return Viewer(subject="amar", teams=(team,), thread_id=None)

    def test_a_document_under_a_team_goes_to_that_team(self, tmp_path):
        store = InMemoryStore()
        sync_corpus(
            _tree(tmp_path, {"teams/platform/runbook.md": "restart the ingester"}),
            store=store,
        )
        found = store.search(
            "restart", scope=Scope.TEAM, viewer=self._member("platform")
        )
        assert found

    def test_another_team_cannot_see_it(self, tmp_path):
        store = InMemoryStore()
        sync_corpus(
            _tree(tmp_path, {"teams/platform/runbook.md": "restart the ingester"}),
            store=store,
        )
        found = store.search(
            "restart", scope=Scope.TEAM, viewer=self._member("finance")
        )
        assert found == []

    def test_it_does_not_land_in_the_shared_corpus(self, tmp_path):
        store = InMemoryStore()
        sync_corpus(
            _tree(tmp_path, {"teams/platform/runbook.md": "restart the ingester"}),
            store=store,
        )
        assert store.search("restart", scope=Scope.AGENT, viewer=ANYONE) == []

    def test_documents_outside_teams_still_go_to_everyone(self, tmp_path):
        store = InMemoryStore()
        sync_corpus(
            _tree(
                tmp_path,
                {
                    "handbook.md": "policy for everyone",
                    "teams/platform/runbook.md": "policy for platform",
                },
            ),
            store=store,
        )
        found = store.search("policy", scope=Scope.AGENT, viewer=ANYONE)
        assert [d.id for d in found] == ["corpus:handbook.md"]

    def test_a_nested_document_keeps_its_team(self, tmp_path):
        store = InMemoryStore()
        sync_corpus(
            _tree(tmp_path, {"teams/platform/hr/leave.md": "policy on leave"}),
            store=store,
        )
        assert store.search("leave", scope=Scope.TEAM, viewer=self._member("platform"))

    def test_a_file_loose_in_teams_is_skipped_and_said(self, tmp_path):
        store = InMemoryStore()
        found = sync_corpus(
            _tree(tmp_path, {"teams/stray.md": "policy for nobody"}), store=store
        )
        assert found.ingested == 0 and found.skipped

    def test_removing_the_folder_removes_the_documents(self, tmp_path):
        store = InMemoryStore()
        root = _tree(tmp_path, {"teams/platform/runbook.md": "restart the ingester"})
        sync_corpus(root, store=store)
        (root / "teams" / "platform" / "runbook.md").unlink()
        sync_corpus(root, store=store)
        assert (
            store.search("restart", scope=Scope.TEAM, viewer=self._member("platform"))
            == []
        )
