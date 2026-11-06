"""What a deployment has interposed on its runs, as the interface sees it."""

from __future__ import annotations

import pytest

from agent.aegra import extension_routes


@pytest.fixture
def declared(monkeypatch):
    def set(entries: list) -> None:
        monkeypatch.setattr(extension_routes, "_declared", lambda: entries)

    return set


@pytest.mark.asyncio
async def test_a_deployment_with_none_says_so_rather_than_failing(declared):
    declared([])
    assert (await extension_routes.list_extensions())["extensions"] == []


@pytest.mark.asyncio
async def test_names_each_one(declared):
    declared(["json:JSONDecoder"])
    found = (await extension_routes.list_extensions())["extensions"]
    assert found[0]["path"] == "json:JSONDecoder"


@pytest.mark.asyncio
async def test_says_whether_the_run_may_proceed_without_it(declared):
    declared(["json:JSONDecoder"])
    found = (await extension_routes.list_extensions())["extensions"]
    assert found[0]["required"] is True


@pytest.mark.asyncio
async def test_an_optional_one_is_marked_so(declared):
    declared([{"path": "json:JSONDecoder", "on_failure": "open"}])
    found = (await extension_routes.list_extensions())["extensions"]
    assert found[0]["required"] is False


@pytest.mark.asyncio
async def test_says_one_that_loads_is_in_the_path(declared):
    declared(["json:JSONDecoder"])
    found = (await extension_routes.list_extensions())["extensions"]
    assert found[0]["loaded"] is True


@pytest.mark.asyncio
async def test_says_one_that_cannot_be_loaded_is_not(declared):
    """An optional extension that is absent is the quiet case."""
    declared([{"path": "nowhere.at.all:Thing", "on_failure": "open"}])
    found = (await extension_routes.list_extensions())["extensions"]
    assert found[0]["loaded"] is False


@pytest.mark.asyncio
async def test_says_why_it_could_not_be_loaded(declared):
    declared([{"path": "nowhere.at.all:Thing", "on_failure": "open"}])
    found = (await extension_routes.list_extensions())["extensions"]
    assert "nowhere" in found[0]["problem"]


@pytest.mark.asyncio
async def test_a_required_one_that_is_missing_is_reported_not_raised(declared):
    """The page must still render; refusing runs is the loader's job."""
    declared(["nowhere.at.all:Thing"])
    found = (await extension_routes.list_extensions())["extensions"]
    assert found[0]["loaded"] is False and found[0]["required"] is True


@pytest.mark.asyncio
async def test_a_malformed_declaration_is_reported_rather_than_hidden(declared):
    declared([{"on_failure": "open"}])
    found = (await extension_routes.list_extensions())["extensions"]
    assert found[0]["problem"]


class TestWhatEachOneCosts:
    """An extension that adds two seconds to every turn is invisible"""

    @pytest.fixture(autouse=True)
    def clean(self):
        from agent.src.infrastructure import extension_metrics

        extension_metrics.timing = extension_metrics.ExtensionTiming()
        return extension_metrics.timing

    @pytest.mark.asyncio
    async def test_one_that_never_ran_reports_no_figures(self, declared):
        declared(["pkg.mod:Thing"])
        found = (await extension_routes.list_extensions())["extensions"][0]
        assert found["timing"] is None

    @pytest.mark.asyncio
    async def test_how_long_it_usually_takes_is_reported(self, declared, clean):
        clean.record("pkg.mod:Thing", seconds=0.2)
        declared(["pkg.mod:Thing"])
        found = (await extension_routes.list_extensions())["extensions"][0]
        assert found["timing"]["average_ms"] == pytest.approx(200, rel=0.01)

    @pytest.mark.asyncio
    async def test_how_often_it_refuses_is_reported(self, declared, clean):
        clean.record("pkg.mod:Thing", seconds=0.1, refused=True)
        clean.record("pkg.mod:Thing", seconds=0.1)
        declared(["pkg.mod:Thing"])
        found = (await extension_routes.list_extensions())["extensions"][0]
        assert found["timing"]["refusal_rate"] == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_figures_follow_the_extension_they_belong_to(self, declared, clean):
        clean.record("pkg.mod:A", seconds=0.3)
        declared(["pkg.mod:A", "pkg.mod:B"])
        found = (await extension_routes.list_extensions())["extensions"]
        by_path = {e["path"]: e for e in found}
        assert by_path["pkg.mod:A"]["timing"]["calls"] == 1
        assert by_path["pkg.mod:B"]["timing"] is None

    @pytest.mark.asyncio
    async def test_an_unreadable_declaration_still_reports_a_timing_field(
        self, declared
    ):
        declared([{"on_failure": "open"}])
        found = (await extension_routes.list_extensions())["extensions"][0]
        assert "timing" in found
