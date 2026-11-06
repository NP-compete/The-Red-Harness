"""Edits that outlive the process that made them."""

from __future__ import annotations

import os

import pytest

psycopg = pytest.importorskip("psycopg")

from agent.src.agent.config.overlay_postgres import (  # noqa: E402
    PostgresOverlay,
)

PROMPT = "config/agent/PROMPT.md"
ROUTER = "config/agent/runtime/router.yaml"


def _dsn() -> str:
    from agent.src.settings import settings

    host = os.environ.get("POSTGRES_HOST", "localhost")
    return (
        f"host={host} port={settings.POSTGRES_PORT} dbname={settings.POSTGRES_DB} "
        f"user={settings.POSTGRES_USER} password={settings.POSTGRES_PASSWORD}"
    )


@pytest.fixture
def overlay():
    """A real store against a real database, on its own table."""
    try:
        with psycopg.connect(_dsn(), connect_timeout=3):
            pass
    except Exception as error:  # pragma: no cover - environment dependent
        pytest.skip(f"no database to test against: {type(error).__name__}")

    table = "config_overlay_test"
    made = PostgresOverlay(dsn=_dsn(), table=table)
    with psycopg.connect(_dsn()) as conn:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
    made.ensure_table()
    yield made
    with psycopg.connect(_dsn()) as conn:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()


class TestItKeepsWhatItIsGiven:
    def test_the_content_comes_back(self, overlay):
        overlay.apply(PROMPT, "new wording", author="ada")
        assert overlay.current(PROMPT) == "new wording"

    def test_a_path_never_edited_has_nothing(self, overlay):
        assert overlay.current(PROMPT) is None

    def test_versions_count_up_per_path(self, overlay):
        overlay.apply(PROMPT, "one", author="ada")
        assert overlay.apply(PROMPT, "two", author="ada").version == 2

    def test_each_path_numbers_separately(self, overlay):
        overlay.apply(PROMPT, "a", author="ada")
        overlay.apply(PROMPT, "b", author="ada")
        assert overlay.apply(ROUTER, "c", author="ada").version == 1

    def test_who_and_when_are_recorded(self, overlay):
        written = overlay.apply(PROMPT, "x", author="ada")
        assert written.author == "ada"
        assert written.at

    def test_an_edit_needs_an_author(self, overlay):
        with pytest.raises(ValueError):
            overlay.apply(PROMPT, "x", author="")


class TestItOutlivesTheProcess:
    def test_another_instance_reads_the_same_rows(self, overlay):
        """The whole point, and the thing memory could not do."""
        overlay.apply(PROMPT, "written by the first", author="ada")

        second = PostgresOverlay(dsn=_dsn(), table=overlay.table)
        second.refresh()
        assert second.current(PROMPT) == "written by the first"

    def test_history_survives_too(self, overlay):
        overlay.apply(PROMPT, "one", author="ada")
        overlay.apply(PROMPT, "two", author="bo")

        second = PostgresOverlay(dsn=_dsn(), table=overlay.table)
        second.refresh()
        assert [one.content for one in second.history(PROMPT)] == ["one", "two"]
        assert [one.author for one in second.history(PROMPT)] == ["ada", "bo"]


class TestNothingIsOverwritten:
    def test_an_earlier_version_is_still_readable(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        overlay.apply(PROMPT, "second", author="bo")
        assert overlay.at_version(PROMPT, 1).content == "first"

    def test_reverting_writes_a_new_version(self, overlay):
        overlay.apply(PROMPT, "first", author="ada")
        overlay.apply(PROMPT, "second", author="bo")
        overlay.revert(PROMPT, to=1, author="cy")
        assert overlay.current(PROMPT) == "first"
        assert [one.version for one in overlay.history(PROMPT)] == [1, 2, 3]

    def test_adopting_the_baseline_is_a_version(self, overlay):
        overlay.apply(PROMPT, "mine", author="ada")
        overlay.adopt_baseline(PROMPT, author="bo")
        assert overlay.current(PROMPT) is None
        assert [one.version for one in overlay.history(PROMPT)] == [1, 2]
        assert overlay.at_version(PROMPT, 1).content == "mine"

    def test_an_adopted_path_is_no_longer_overridden(self, overlay):
        overlay.apply(PROMPT, "mine", author="ada")
        overlay.adopt_baseline(PROMPT, author="ada")
        assert overlay.overridden() == []


class TestOnePodSeesAnother:
    def test_an_edit_elsewhere_moves_the_generation_here(self, overlay):
        here = PostgresOverlay(dsn=_dsn(), table=overlay.table)
        here.refresh()
        before = here.generation

        overlay.apply(PROMPT, "changed over there", author="ada")

        here.refresh()
        assert here.generation != before

    def test_and_the_content_arrives_with_it(self, overlay):
        here = PostgresOverlay(dsn=_dsn(), table=overlay.table)
        here.refresh()
        overlay.apply(PROMPT, "changed over there", author="ada")
        here.refresh()
        assert here.current(PROMPT) == "changed over there"

    def test_it_is_not_instant_and_this_says_so(self, overlay):
        here = PostgresOverlay(dsn=_dsn(), table=overlay.table)
        here.refresh()
        overlay.apply(PROMPT, "changed over there", author="ada")
        assert here.current(PROMPT) is None


class TestItLooksLikeTheOtherStore:
    def test_the_same_methods_are_there(self, overlay):
        from agent.src.agent.config.overlay import InMemoryOverlay

        for name in (
            "apply",
            "adopt_baseline",
            "revert",
            "current",
            "at_version",
            "history",
            "overridden",
            "generation",
        ):
            assert hasattr(overlay, name), name
            assert hasattr(InMemoryOverlay(), name), name

    def test_reverting_to_a_version_that_never_existed_is_refused(self, overlay):
        from agent.src.agent.config.overlay import NothingToRevertTo

        overlay.apply(PROMPT, "one", author="ada")
        with pytest.raises(NothingToRevertTo):
            overlay.revert(PROMPT, to=7, author="cy")
